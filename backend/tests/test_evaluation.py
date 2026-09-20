from pathlib import Path
from unittest.mock import patch
import json

import pytest

from app.extraction import extract_candidates
from app.ingestion import classify_file, ingest_document


FIXTURES = Path(__file__).parent / "fixtures"


def field_metrics(expected_names: set[str], extracted_names: set[str]) -> tuple[float, float]:
    true_positives = len(expected_names & extracted_names)
    precision = true_positives / len(extracted_names) if extracted_names else 0.0
    recall = true_positives / len(expected_names) if expected_names else 1.0
    return precision, recall


def test_anonymized_fixture_precision_recall_is_recorded() -> None:
    cases = [
        ("clean_report.txt", {"Hemoglobin", "Total Cholesterol", "TSH"}),
        ("clarifylabs_sample_report.txt", {"Hemoglobin", "White Blood Cell Count", "Platelet Count", "Total Cholesterol", "LDL Cholesterol", "HDL Cholesterol", "Triglycerides", "TSH", "Free T4"}),
        ("noisy_report.txt", {"Hb", "Creatinine", "ALT"}),
    ]
    metrics = []
    for fixture_name, expected in cases:
        extracted = {result["raw_test_name"] for result in extract_candidates((FIXTURES / fixture_name).read_text())}
        metrics.append(field_metrics(expected, extracted))

    assert all(precision >= 0.7 and recall >= 0.7 for precision, recall in metrics)


def test_unsupported_file_type_has_clear_error() -> None:
    with pytest.raises(ValueError, match="Upload a PDF, JPG, or PNG file"):
        classify_file("text/plain", "report.txt")


def test_low_ocr_confidence_has_clear_error() -> None:
    with patch("app.ingestion._ocr_payload", return_value=("Hemoglobin 13.4 g/dL", 0.12)):
        result = ingest_document(b"image", "image/png", "blurry.png")

    assert result.error is not None
    assert "too unclear" in result.error or "reliably read" in result.error


def test_synthetic_image_corpus_has_ground_truth_for_ocr_runs() -> None:
    corpus = FIXTURES / "image_samples"
    ground_truth = json.loads((corpus / "ground_truth.json").read_text())

    for filename, expected_names in ground_truth["samples"].items():
        image = corpus / filename
        assert image.is_file()
        assert image.stat().st_size > 0
        assert expected_names
