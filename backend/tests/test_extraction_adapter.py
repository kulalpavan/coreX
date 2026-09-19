import pytest

from app.extraction_adapter import deterministic_to_schema, extract_with_fallback, structured_to_candidates, validate_model_output


TEXT = "Report Date: 2026-08-14\nHemoglobin 13.8 g/dL 12.0 - 15.5 Normal"


def test_deterministic_parser_maps_into_fixed_schema() -> None:
    result = deterministic_to_schema(TEXT)

    assert result.report_date == "2026-08-14"
    assert result.tests[0].test_name == "Hemoglobin"
    assert result.tests[0].value == 13.8
    assert result.tests[0].confidence.value > 0


def test_invalid_model_output_is_rejected() -> None:
    with pytest.raises(ValueError, match="schema validation"):
        validate_model_output({"report_date": None, "tests": [{"test_name": "Hb", "confidence": {}}]})


def test_model_provider_failure_falls_back_to_deterministic_parser() -> None:
    class BrokenProvider:
        def extract(self, raw_text: str) -> dict:
            raise ValueError("malformed JSON")

    result = extract_with_fallback(TEXT, BrokenProvider())

    assert result.tests[0].test_name == "Hemoglobin"


def test_valid_provider_output_is_accepted_and_normalized() -> None:
    class Provider:
        def extract(self, raw_text: str) -> dict:
            return {
                "report_date": "2026-08-14",
                "tests": [{
                    "test_name": "Glucose",
                    "value": 5.0,
                    "unit": "mmol/L",
                    "reference_range": {"low": 3.9, "high": 5.6},
                    "confidence": {"test_name": 0.9, "value": 0.8, "unit": 0.9, "reference_range": 0.7},
                }],
            }

    result = extract_with_fallback("ignored", Provider())
    candidate = structured_to_candidates(result)[0]

    assert candidate["unit"] == "mg/dL"
    assert candidate["value"] == 90.0
    assert candidate["review_required"] is True


def test_markdown_wrapped_provider_json_is_accepted() -> None:
    class Provider:
        def extract(self, raw_text: str) -> str:
            return "```json\n{\"report_date\": null, \"tests\": [{\"test_name\": \"TSH\", \"value\": 2.4, \"confidence\": {\"test_name\": 0.9, \"value\": 0.9, \"unit\": 0.2, \"reference_range\": 0.2}}]}\n```"

    result = extract_with_fallback("ignored", Provider())

    assert result.tests[0].test_name == "TSH"


@pytest.mark.parametrize(
    "payload",
    [
        {"report_date": None, "tests": [{"test_name": "Hb", "value": "13.4", "confidence": {"test_name": 1, "value": 1, "unit": 1, "reference_range": 1}}]},
        {"report_date": None, "tests": [{"test_name": "Hb", "value": 13.4, "reference_range": {"low": 16, "high": 12}, "confidence": {"test_name": 1, "value": 1, "unit": 1, "reference_range": 1}}]},
    ],
)
def test_unsafe_provider_payload_is_rejected(payload: dict) -> None:
    with pytest.raises(ValueError):
        validate_model_output(payload)
