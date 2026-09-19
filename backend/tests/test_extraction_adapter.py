import pytest
import json
from unittest.mock import patch

from app.extraction_adapter import LLMExtractionProvider, deterministic_to_schema, extract_report_results_with_metadata, extract_with_fallback, merge_provider_results, structured_to_candidates, validate_model_output


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


def test_openrouter_free_provider_sends_chat_request_and_parses_response() -> None:
    class Response:
        def read(self) -> bytes:
            return json.dumps({
                "choices": [{"message": {"content": json.dumps({
                    "report_date": None,
                    "tests": [{
                        "test_name": "TSH",
                        "value": 2.4,
                        "confidence": {"test_name": 0.9, "value": 0.9, "unit": 0.2, "reference_range": 0.2},
                    }],
                })}}]
            }).encode()

    provider = LLMExtractionProvider("https://openrouter.ai/api/v1/chat/completions", "test-key")
    with patch("app.extraction_adapter.urlopen", return_value=Response()) as request:
        result = provider.extract("TSH 2.4")

    sent = json.loads(request.call_args.args[0].data.decode())
    assert sent["model"] == "openrouter/free"
    assert sent["response_format"] == {"type": "json_object"}
    assert result["tests"][0]["test_name"] == "TSH"


def test_conflicting_provider_value_keeps_deterministic_value_and_flags_review() -> None:
    deterministic = [{"raw_test_name": "Hemoglobin", "canonical_test_id": "hemoglobin", "value": 13.4, "unit": "g/dL", "reference_range_low": 12.0, "reference_range_high": 15.5}]
    model = [{"raw_test_name": "Hemoglobin", "canonical_test_id": "hemoglobin", "value": 14.4, "unit": "g/dL", "reference_range_low": 12.0, "reference_range_high": 15.5}]

    merged = merge_provider_results(deterministic, model)

    assert merged[0]["value"] == 13.4
    assert merged[0]["review_required"] is True
    assert merged[0]["extraction_conflict"] is True
