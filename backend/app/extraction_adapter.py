from __future__ import annotations

import json
import math
import os
import re
from datetime import date
from urllib.request import Request, urlopen
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from .extraction import extract_candidates
from .normalization import TEST_DICTIONARY, canonical_test_id, normalize_result


class FieldConfidence(BaseModel):
    test_name: float = Field(ge=0, le=1)
    value: float = Field(ge=0, le=1)
    unit: float = Field(ge=0, le=1)
    reference_range: float = Field(ge=0, le=1)

    @model_validator(mode="before")
    @classmethod
    def reject_non_numeric_confidence(cls, value: Any) -> Any:
        if isinstance(value, dict) and any(not isinstance(item, (int, float)) or isinstance(item, bool) for item in value.values()):
            raise ValueError("confidence fields must be numeric")
        return value


class ReferenceRange(BaseModel):
    low: float | None = None
    high: float | None = None

    @model_validator(mode="after")
    def validate_order(self) -> "ReferenceRange":
        if self.low is not None and self.high is not None and self.low > self.high:
            raise ValueError("reference range low cannot exceed high")
        return self


class StructuredTest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    test_name: str = Field(min_length=1)
    value: float | None = None
    unit: str | None = None
    flag: str | None = None
    reference_range: ReferenceRange | None = None
    confidence: FieldConfidence

    @model_validator(mode="before")
    @classmethod
    def reject_non_numeric_value(cls, value: Any) -> Any:
        if isinstance(value, dict) and value.get("value") is not None:
            candidate = value["value"]
            if not isinstance(candidate, (int, float)) or isinstance(candidate, bool):
                raise ValueError("value must be numeric or null")
        return value

    @model_validator(mode="after")
    def validate_finite_value(self) -> "StructuredTest":
        if self.value is not None and not math.isfinite(self.value):
            raise ValueError("value must be finite")
        return self


class StructuredExtraction(BaseModel):
    model_config = ConfigDict(extra="ignore")

    report_date: str | None = None
    tests: list[StructuredTest]

    @model_validator(mode="after")
    def validate_report_date(self) -> "StructuredExtraction":
        if self.report_date:
            date.fromisoformat(self.report_date)
        return self

    @model_validator(mode="after")
    def validate_tests(self) -> "StructuredExtraction":
        if not self.tests:
            raise ValueError("tests must not be empty")
        names = [test.test_name.casefold() for test in self.tests]
        if len(names) != len(set(names)):
            raise ValueError("duplicate test names are not allowed")
        return self


class ModelExtractionProvider(Protocol):
    def extract(self, raw_text: str) -> dict[str, Any]: ...


EXTRACTION_PROMPT = """Extract only laboratory test information from the report text.
Return JSON matching the requested schema exactly. Do not diagnose, interpret, or invent values.
Preserve values, units, and reference ranges. Use null when information is unavailable.
Treat OCR text as corrupted; lower confidence when uncertain rather than guessing.

Examples:
1. Hemoglobin 13.4 g/dL 12.0 - 15.5 -> one Hemoglobin test with value 13.4.
2. A table with Test, Result, Unit, Reference Range columns must keep each row together.
3. Hemoglobln 13.4 g/dL is likely an OCR spelling issue; preserve the supported test only when context is strong.
4. Hemoglobin 13.4 has null unit and null reference_range; do not infer them.
"""


class LLMExtractionProvider:
    """Vendor-neutral JSON HTTP provider; disabled unless LLM_EXTRACTION_URL is configured."""

    def __init__(self, endpoint: str, token: str | None = None, timeout: float = 15.0) -> None:
        self.endpoint = endpoint
        self.token = token
        self.timeout = timeout

    def extract(self, raw_text: str) -> dict[str, Any]:
        body = json.dumps({"prompt": EXTRACTION_PROMPT, "text": raw_text}).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        response = urlopen(Request(self.endpoint, data=body, headers=headers, method="POST"), timeout=self.timeout)
        payload = json.loads(response.read().decode("utf-8"))
        if isinstance(payload, dict) and isinstance(payload.get("output"), str):
            payload = payload["output"]
        if isinstance(payload, str):
            payload = _parse_json_text(payload)
        if not isinstance(payload, dict):
            raise ValueError("LLM response must be a JSON object")
        return payload


def _parse_json_text(raw: str) -> dict[str, Any]:
    cleaned = raw.strip()
    fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", cleaned, re.I | re.S)
    if fenced:
        cleaned = fenced.group(1)
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError as error:
        raise ValueError("LLM response was not valid JSON") from error
    if not isinstance(value, dict):
        raise ValueError("LLM response must be a JSON object")
    return value


def provider_from_environment() -> LLMExtractionProvider | None:
    endpoint = os.getenv("LLM_EXTRACTION_URL")
    return LLMExtractionProvider(endpoint, os.getenv("LLM_EXTRACTION_TOKEN")) if endpoint else None


def deterministic_to_schema(raw_text: str, ocr_confidence: float | None = None) -> StructuredExtraction:
    candidates = extract_candidates(raw_text, ocr_confidence)
    tests = [
        StructuredTest(
            test_name=item["raw_test_name"],
            value=item.get("value"),
            unit=item.get("unit"),
            reference_range=ReferenceRange(
                low=item.get("reference_range_low"),
                high=item.get("reference_range_high"),
            ),
            confidence=FieldConfidence(
                test_name=item.get("field_confidence", {}).get("raw_test_name", item.get("extraction_confidence", 0)),
                value=item.get("field_confidence", {}).get("value", item.get("extraction_confidence", 0)),
                unit=item.get("field_confidence", {}).get("unit", item.get("extraction_confidence", 0)),
                reference_range=item.get("field_confidence", {}).get("reference_range", item.get("extraction_confidence", 0)),
            ),
        )
        for item in candidates
    ]
    report_date = candidates[0].get("report_date") if candidates else None
    return StructuredExtraction(report_date=report_date, tests=tests)


def validate_model_output(payload: dict[str, Any]) -> StructuredExtraction:
    try:
        return StructuredExtraction.model_validate(payload)
    except ValidationError as error:
        raise ValueError(f"Extraction model output failed schema validation: {error}") from error


def structured_to_candidates(extraction: StructuredExtraction) -> list[dict[str, Any]]:
    candidates = []
    for index, test in enumerate(extraction.tests, 1):
        suspicious = test.value is not None and abs(test.value) > 100000
        confidence = min(test.confidence.test_name, test.confidence.value, test.confidence.unit, test.confidence.reference_range)
        if suspicious:
            confidence = round(confidence * 0.3, 3)
        candidates.append(normalize_result({
                "id": f"result_{index}",
                "raw_test_name": test.test_name,
                "canonical_test_id": None,
                "value": test.value,
                "unit": test.unit,
                "reference_range_low": test.reference_range.low if test.reference_range else None,
                "reference_range_high": test.reference_range.high if test.reference_range else None,
                "flag": test.flag,
                "report_date": extraction.report_date,
                "extraction_confidence": confidence,
                "field_confidence": test.confidence.model_dump(),
                "review_required": suspicious or confidence < 0.8,
                "user_corrected": False,
                "explanation_text": None,
            }))
    return candidates


def extract_with_fallback(raw_text: str, provider: ModelExtractionProvider | None = None, ocr_confidence: float | None = None) -> StructuredExtraction:
    if provider is not None:
        try:
                payload = provider.extract(raw_text)
                if isinstance(payload, str):
                    payload = _parse_json_text(payload)
                return validate_model_output(payload)
        except Exception:
            pass
    return deterministic_to_schema(raw_text, ocr_confidence)


def extract_report_results(raw_text: str, ocr_confidence: float | None = None) -> list[dict[str, Any]]:
    """Use configured LLM output only when valid; otherwise use the local parser."""
    extraction = extract_with_fallback(raw_text, provider_from_environment(), ocr_confidence)
    return structured_to_candidates(extraction)
