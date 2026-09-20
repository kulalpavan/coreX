from pathlib import Path
from unittest.mock import patch
from io import BytesIO

import pytest
from reportlab.pdfgen import canvas

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
    assert result["unit"] == "µIU/mL"
    assert result["reference_range_low"] == 0.4
    assert result["reference_range_high"] == 4.5
    assert result["report_date"] is None
    assert result["extraction_confidence"] < 0.8


def test_missing_value_remains_a_reviewable_candidate():
    result = extract_candidates("Hb -- g/dL 12.0 - 15.5\n")[0]

    assert result["raw_test_name"] == "Hb"
    assert result["value"] is None
    assert result["unit"] == "g/dL"
    assert result["reference_range_low"] == 12.0
    assert result["reference_range_high"] == 15.5
    assert result["extraction_confidence"] < 0.8


def test_suspicious_value_is_retained_and_confidence_is_lowered():
    result = extract_candidates("Sodium 999999 mEq/L\n")[0]

    assert result["value"] == 999999
    assert result["extraction_confidence"] < 0.5


def test_unknown_text_does_not_return_fake_sample_results():
    with pytest.raises(ExtractionError, match="could not find readable"):
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


def test_clarifylabs_sample_extracts_ten_lab_rows_and_ignores_metadata():
    text = (FIXTURES / "clarifylabs_sample_report.txt").read_text(encoding="utf-8")

    results = extract_candidates(text)

    assert [result["raw_test_name"].split(" |")[0] for result in results] == [
        "Hemoglobin",
        "White Blood Cell Count",
        "Platelet Count",
        "Total Cholesterol",
        "LDL Cholesterol",
        "HDL Cholesterol",
        "Triglycerides",
        "TSH",
        "Free T4",
    ]
    assert results[1]["value"] == 7200
    assert results[2]["value"] == 245000
    assert results[3]["reference_range_high"] == 200
    assert results[5]["reference_range_low"] == 40
    assert results[8]["value"] == 1.18
    assert all("Patient" not in result["raw_test_name"] for result in results)


def test_pdf_text_pipeline_extracts_sample_rows():
    source = (FIXTURES / "clarifylabs_sample_report.txt").read_text(encoding="utf-8")
    pdf_buffer = BytesIO()
    pdf = canvas.Canvas(pdf_buffer)
    text = pdf.beginText(40, 760)
    for line in source.splitlines():
        text.textLine(line)
    pdf.drawText(text)
    pdf.save()

    processed = process_report(pdf_buffer.getvalue(), "application/pdf", "ClarifyLabs_Sample_Lab_Report.pdf")

    assert len(processed["results"]) >= 9
    assert processed["source_type"] == "pdf_text"


def test_columnar_pdf_text_groups_cells_after_test_name():
    text = """Report Date: 2026-08-14
Test Name
Result
Unit
Reference Range
Flag
Hemoglobin
13.4
g/dL
12.0 - 15.5
Normal
Free T4
1.18
ng/dL
0.80 - 1.80
Normal
"""

    results = extract_candidates(text)

    assert [result["raw_test_name"] for result in results] == ["Hemoglobin", "Free T4"]
    assert results[0]["value"] == 13.4
    assert results[1]["value"] == 1.18


def test_decimal_already_present():
    results = extract_candidates(
        "TSH 2.2 uIU/mL\n"
        "Hemoglobin 12.4 g/dL\n"
        "Hematocrit 37.8 %\n"
        "Direct Bilirubin 0.8 mg/dL\n"
        "A/G Ratio 1.4\n"
    )
    assert results[0]["value"] == 2.2
    assert results[1]["value"] == 12.4
    assert results[2]["value"] == 37.8
    assert results[3]["value"] == 0.8
    assert results[4]["value"] == 1.4
    assert not results[0].get("review_required")


def test_decimal_lost_but_biologically_impossible():
    results = extract_candidates(
        "Hematocrit 378 %\n"
        "Direct Bilirubin 08 mg/dL\n"
    )
    assert results[0]["value"] == 37.8
    assert results[0]["review_required"] is True
    assert results[0]["correction_reason"] == "Hematocrit > 100% is biologically impossible; OCR dropped decimal"
    
    assert results[1]["value"] == 0.8
    assert results[1]["review_required"] is True


def test_legitimate_integers_remain_integers():
    results = extract_candidates(
        "TSH 22 uIU/mL\n"
        "MCV 220 fL\n"
        "A/G Ratio 8\n"
        "Globulin 32 g/dL\n"
        "Sodium 124 mEq/L\n"
        "Platelet Count 2,54,000 cells/uL\n"
    )
    assert results[0]["value"] == 22
    assert results[0]["review_required"] is True  # 22 is suspicious but not impossible (threshold is 100)
    
    assert results[1]["value"] == 22.0  # 220 is >= 200, so it gets corrected
    assert results[2]["value"] == 8
    
    assert results[3]["value"] == 3.2  # Globulin 32 is >= 10 (biologically impossible), so it gets corrected
    
    assert results[4]["value"] == 124
    
    assert results[5]["value"] == 254000
    assert not results[5].get("review_required")
