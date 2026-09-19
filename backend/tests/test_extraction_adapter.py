import pytest

from app.extraction_adapter import deterministic_to_schema, extract_with_fallback, validate_model_output


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
