from pathlib import Path
from unittest.mock import patch

import pytest

from app.extraction import ExtractionError, extract_candidates, process_report
from app.ingestion import IngestionResult, classify_file, ingest_document
from app.normalization import normalize_result


FIXTURES = Path(__file__).parent / "fixtures"


def test_clean_text_report_extracts_candidates_and_preserves_raw_names():
    text = (FIXTURES / "clean_report.txt").read_text()
    results = extract_candidates(text)

    assert [result["raw_test_name"] for result in results] == [
        "Hemoglobin",
        "Total Cholesterol",
        "TSH",
    ]
    assert results[0]["report_date"] == "2026-08-14"
    assert results[0]["canonical_test_id"] == "hemoglobin"
    assert results[0]["user_corrected"] is False
    assert 0 <= results[0]["extraction_confidence"] <= 1


def test_missing_unit_and_range_are_null_without_guessing():
    result = extract_candidates("TSH 2.4\n")[0]

    assert result["value"] == 2.4
    assert result["unit"] is None
    assert result["reference_range_low"] is None
    assert result["reference_range_high"] is None
    assert result["report_date"] is None
    assert result["extraction_confidence"] < 0.8


def test_missing_value_remains_a_reviewable_candidate():
    result = extract_candidates("Hb -- g/dL 12.0 - 15.5\n")[0]

    assert result["raw_test_name"] == "Hb"
    assert result["value"] is None
    assert result["unit"] == "g/dL"
    assert result["reference_range_low"] == 12.0
    assert result["reference_range_high"] == 15.5
    assert result["extraction_confidence"] < 0.5


def test_suspicious_value_is_retained_and_confidence_is_lowered():
    result = extract_candidates("Creatinine 999999 mg/dL\n")[0]

    assert result["value"] == 999999
    assert result["extraction_confidence"] < 0.5


def test_unknown_text_does_not_return_fake_sample_results():
    with pytest.raises(ExtractionError, match="No recognizable"):
        extract_candidates("This is not a laboratory report.")


def test_noisy_fixture_remains_reviewable():
    results = extract_candidates((FIXTURES / "noisy_report.txt").read_text())

    assert any(result["raw_test_name"] == "Creatinine" for result in results)
    assert all(result["user_corrected"] is False for result in results)


def test_safe_unit_conversions():
    glucose = normalize_result({"raw_test_name": "Glucose", "value": 5.0, "unit": "mmol/L"})
    creatinine = normalize_result({"raw_test_name": "Creatinine", "value": 88.4, "unit": "umol/L"})

    assert glucose["canonical_test_id"] == "glucose"
    assert glucose["unit"] == "mg/dL"
    assert glucose["value"] == 90.0
    assert creatinine["unit"] == "mg/dL"
    assert creatinine["value"] == 1.0


def test_unsupported_conversion_preserves_original_unit():
    result = normalize_result({"raw_test_name": "TSH", "value": 2.4, "unit": "unknown"})

    assert result["unit"] == "unknown"
    assert result["value"] == 2.4


def test_file_classification_and_empty_document_state():
    assert classify_file("application/pdf", "report.pdf") == "pdf"
    assert classify_file("image/png", "report.png") == "image"
    empty = ingest_document(b"", "image/png", "empty.png")
    assert empty.error == "The uploaded document is empty."


def test_image_processing_uses_ocr_adapter_and_returns_metadata():
    ingestion = IngestionResult("Hb 11.2 g/dL 12.0 - 15.5 L", "image", 0.62)
    with patch("app.extraction.ingest_document", return_value=ingestion):
        processed = process_report(b"image", "image/png", "report.png")

    assert processed["source_type"] == "image"
    assert processed["ocr_confidence"] == 0.62
    assert processed["results"][0]["raw_test_name"] == "Hb"
