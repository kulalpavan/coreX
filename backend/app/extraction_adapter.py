from __future__ import annotations

import json
import math
import os
import re
from dataclasses import dataclass
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


@dataclass(frozen=True)
class ExtractionRun:
    results: list[dict[str, Any]]
    provider: str
    fallback_used: bool
    fallback_reason: str | None = None


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
    """OpenAI-compatible JSON provider; disabled unless an endpoint is configured."""

    def __init__(self, endpoint: str, token: str | None = None, model: str = "openrouter/free", timeout: float = 15.0) -> None:
        self.endpoint = endpoint
        self.token = token
        self.model = model
        self.timeout = timeout

    def extract(self, raw_text: str) -> dict[str, Any]:
        body = json.dumps(
            {
                "model": self.model,
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": EXTRACTION_PROMPT},
                    {"role": "user", "content": raw_text},
                ],
            }
        ).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        response = urlopen(Request(self.endpoint, data=body, headers=headers, method="POST"), timeout=self.timeout)
        payload = json.loads(response.read().decode("utf-8"))
        choices = payload.get("choices") if isinstance(payload, dict) else None
        if choices and isinstance(choices[0], dict):
            message = choices[0].get("message", {})
            payload = message.get("content")
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
    token = os.getenv("LLM_EXTRACTION_TOKEN")
    endpoint = os.getenv("LLM_EXTRACTION_URL")
    if not token and not endpoint:
        return None
    return LLMExtractionProvider(
        endpoint or "https://openrouter.ai/api/v1/chat/completions",
        token,
        os.getenv("LLM_EXTRACTION_MODEL", "openrouter/free"),
    )


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


def _candidate_key(candidate: dict[str, Any]) -> str:
    return (candidate.get("canonical_test_id") or candidate.get("raw_test_name", "")).casefold()


def merge_provider_results(deterministic: list[dict[str, Any]], model: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep deterministic values on conflict and surface the disagreement for review."""
    model_by_key = {_candidate_key(item): item for item in model}
    merged = []
    for item in deterministic:
        candidate = dict(item)
        model_item = model_by_key.pop(_candidate_key(item), None)
        if model_item:
            conflicts = any(
                candidate.get(field) != model_item.get(field)
                for field in ("value", "unit", "reference_range_low", "reference_range_high")
            )
            if conflicts:
                candidate["review_required"] = True
                candidate["extraction_conflict"] = True
        merged.append(candidate)
    for item in model_by_key.values():
        candidate = dict(item)
        candidate["review_required"] = True
        candidate["extraction_conflict"] = True
        merged.append(candidate)
    return merged


def _call_provider_with_retry(provider: ModelExtractionProvider, raw_text: str) -> StructuredExtraction:
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            payload = provider.extract(raw_text)
            if isinstance(payload, str):
                payload = _parse_json_text(payload)
            return validate_model_output(payload)
        except Exception as error:
            last_error = error
            if attempt == 0:
                continue
    raise last_error or ValueError("provider failed")


def extract_report_results_with_metadata(raw_text: str, ocr_confidence: float | None = None) -> ExtractionRun:
    deterministic = [normalize_result(item) for item in extract_candidates(raw_text, ocr_confidence)]
    provider = provider_from_environment()
    if provider is None:
        return ExtractionRun(deterministic, "deterministic", False)
    try:
        model = structured_to_candidates(_call_provider_with_retry(provider, raw_text))
        merged = merge_provider_results(deterministic, model)
        return ExtractionRun(merged, "openrouter", False)
    except TimeoutError:
        return ExtractionRun(deterministic, "deterministic", True, "timeout")
    except (ValueError, TypeError, KeyError, OSError) as error:
        return ExtractionRun(deterministic, "deterministic", True, type(error).__name__.lower())


def extract_report_results(raw_text: str, ocr_confidence: float | None = None) -> list[dict[str, Any]]:
    """Use configured LLM output only when valid; otherwise use the local parser."""
    return extract_report_results_with_metadata(raw_text, ocr_confidence).results
