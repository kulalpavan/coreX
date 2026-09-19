from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from .extraction import extract_candidates


class FieldConfidence(BaseModel):
    test_name: float = Field(ge=0, le=1)
    value: float = Field(ge=0, le=1)
    unit: float = Field(ge=0, le=1)
    reference_range: float = Field(ge=0, le=1)


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

    test_name: str
    value: float | None = None
    unit: str | None = None
    reference_range: ReferenceRange = ReferenceRange()
    confidence: FieldConfidence


class StructuredExtraction(BaseModel):
    model_config = ConfigDict(extra="ignore")

    report_date: str | None = None
    tests: list[StructuredTest]


class ModelExtractionProvider(Protocol):
    def extract(self, raw_text: str) -> dict[str, Any]: ...


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
    return StructuredExtraction(report_date=candidates[0].get("report_date") if candidates else None, tests=tests)


def validate_model_output(payload: dict[str, Any]) -> StructuredExtraction:
    try:
        return StructuredExtraction.model_validate(payload)
    except ValidationError as error:
        raise ValueError(f"Extraction model output failed schema validation: {error}") from error


def extract_with_fallback(raw_text: str, provider: ModelExtractionProvider | None = None, ocr_confidence: float | None = None) -> StructuredExtraction:
    if provider is not None:
        try:
            return validate_model_output(provider.extract(raw_text))
        except (ValueError, TypeError, KeyError):
            pass
    return deterministic_to_schema(raw_text, ocr_confidence)
