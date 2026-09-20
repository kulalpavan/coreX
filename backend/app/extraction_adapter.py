from __future__ import annotations

import json
import math
import os
import re
from dataclasses import dataclass
from datetime import date
from urllib.request import Request, urlopen
import urllib.error
import time
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
Return a JSON object matching the following structure exactly. Do not diagnose, interpret, or invent values.
Preserve values, units, and reference ranges. Use null when information is unavailable.
Treat OCR text as corrupted; lower confidence when uncertain rather than guessing.

EXPECTED JSON SCHEMA:
{
  "report_date": "YYYY-MM-DD" or null,
  "tests": [
    {
      "test_name": "Name of the test",
      "value": 123.45 (numeric) or null,
      "unit": "g/dL" or null,
      "flag": "H" or "L" or "normal" or null,
      "reference_range": {
        "low": 12.0 or null,
        "high": 15.5 or null
      } or null,
      "confidence": {
        "test_name": 0.9,
        "value": 0.9,
        "unit": 0.9,
        "reference_range": 0.9
      }
    }
  ]
}

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


def _sanitize_for_api(text: str) -> str:
    """Strip non-printable / non-ASCII control characters that cause Gemini 400 errors."""
    # Keep normal ASCII printable + newline + tab; replace everything else with a space
    sanitized = re.sub(r"[^\x09\x0A\x0D\x20-\x7E\xA0-\xFF]", " ", text)
    # Collapse runs of whitespace but preserve newlines
    sanitized = re.sub(r"[^\S\n]+", " ", sanitized)
    return sanitized.strip()


class GeminiExtractionProvider:
    """Gemini native API JSON provider."""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash", timeout: float = 60.0) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def extract(self, raw_text: str) -> dict[str, Any]:
        # Sanitize OCR text to avoid Gemini 400 errors from control characters
        sanitized = _sanitize_for_api(raw_text)
        payload = {
            "system_instruction": {"parts": [{"text": EXTRACTION_PROMPT}]},
            "contents": [{"role": "user", "parts": [{"text": sanitized}]}],
            "generationConfig": {
                "temperature": 0,
                "response_mime_type": "application/json"
            }
        }
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        
        max_retries = 3
        backoff = 2.0
        
        for attempt in range(max_retries + 1):
            try:
                response = urlopen(Request(url, data=body, headers=headers, method="POST"), timeout=self.timeout)
                data = json.loads(response.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    error_body = e.read().decode("utf-8")
                    
                    # Stop if Daily Free Tier Quota is completely exhausted
                    if "GenerateRequestsPerDayPerProjectPerModel-FreeTier" in error_body:
                        raise ValueError("Gemini daily free-tier quota exhausted. Will use deterministic fallback.")
                        
                    # Otherwise it's a temporary rate-limit, apply exponential backoff
                    if attempt < max_retries:
                        retry_after = e.headers.get("Retry-After")
                        delay = float(retry_after) if retry_after else backoff
                        time.sleep(delay)
                        backoff *= 2
                        continue
                raise

        try:
            content = data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            raise ValueError("Unexpected response format from Gemini")
            
        if isinstance(content, str):
            content = _parse_json_text(content)
        if not isinstance(content, dict):
            raise ValueError("LLM response must be a JSON object")
        return content


def provider_from_environment() -> ModelExtractionProvider | None:
    token = os.getenv("LLM_EXTRACTION_TOKEN")
    endpoint = os.getenv("LLM_EXTRACTION_URL")
    
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not token and not endpoint and gemini_key:
        return GeminiExtractionProvider(gemini_key)
        
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
    """Use model values, falling back to deterministic if the model missed a row."""
    deterministic_by_key = {_candidate_key(item): item for item in deterministic}
    merged = []
    for model_item in model:
        candidate = dict(model_item)
        det_item = deterministic_by_key.pop(_candidate_key(model_item), None)
        if det_item:
            conflicts = any(
                candidate.get(field) != det_item.get(field)
                for field in ("value", "unit", "reference_range_low", "reference_range_high")
            )
            if conflicts:
                candidate["review_required"] = True
                candidate["extraction_conflict"] = True
        merged.append(candidate)
    for det_item in deterministic_by_key.values():
        candidate = dict(det_item)
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
        except urllib.error.HTTPError as error:
            # Let HTTP errors (which couldn't be retried in the provider) bubble up immediately
            raise error
        except ValueError as error:
            if "quota exhausted" in str(error):
                raise error
            last_error = error
            if attempt == 0:
                continue
        except Exception as error:
            last_error = error
            if attempt == 0:
                continue
    raise last_error or ValueError("provider failed")


def _reassign_ids(results: list[dict[str, Any]]) -> None:
    """Reassign sequential unique IDs to avoid React key collisions after merge/dedup."""
    for index, item in enumerate(results, 1):
        item["id"] = f"result_{index}"


def extract_report_results_with_metadata(raw_text: str, ocr_confidence: float | None = None) -> ExtractionRun:
    # NOTE: extract_candidates already calls normalize_result internally via _build_result.
    # Do NOT call normalize_result again here — that would corrupt converted values.
    deterministic = list(extract_candidates(raw_text, ocr_confidence))
    provider = provider_from_environment()
    if provider is None:
        _reassign_ids(deterministic)
        return ExtractionRun(deterministic, "deterministic", False)
    try:
        model = structured_to_candidates(_call_provider_with_retry(provider, raw_text))
        merged = merge_provider_results(deterministic, model)
        _reassign_ids(merged)
        provider_name = "gemini" if isinstance(provider, GeminiExtractionProvider) else "openrouter"
        return ExtractionRun(merged, provider_name, False)
    except TimeoutError:
        _reassign_ids(deterministic)
        return ExtractionRun(deterministic, "deterministic", True, "timeout")
    except (ValueError, TypeError, KeyError, OSError) as error:
        import logging
        logging.getLogger(__name__).warning("Extraction provider failed, using deterministic fallback: %s: %s", type(error).__name__, error)
        _reassign_ids(deterministic)
        return ExtractionRun(deterministic, "deterministic", True, type(error).__name__.lower())


def extract_report_results(raw_text: str, ocr_confidence: float | None = None) -> list[dict[str, Any]]:
    """Use configured LLM output only when valid; otherwise use the local parser."""
    return extract_report_results_with_metadata(raw_text, ocr_confidence).results
