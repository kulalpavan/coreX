from unittest.mock import patch

from fastapi.testclient import TestClient

from app.ingestion import get_ocr_status, get_pdf_text_status
from app.main import app


client = TestClient(app)


def test_health_exposes_ocr_and_pdf_capabilities() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert "ocr_available" in body
    assert "tesseract_version" in body
    assert "pdf_text_extraction_available" in body


def test_tesseract_unavailable_is_non_fatal() -> None:
    with patch("pytesseract.get_tesseract_version", side_effect=RuntimeError("missing")):
        status = get_ocr_status()

    assert status["available"] is False
    assert status["version"] is None
    assert "not installed" in status["error"]


def test_tesseract_available_reports_version() -> None:
    with patch("pytesseract.get_tesseract_version", return_value="5.3.0"):
        status = get_ocr_status()

    assert status["available"] is True
    assert status["version"] == "5.3.0"


def test_pdf_text_extraction_status_is_available_in_test_environment() -> None:
    assert get_pdf_text_status()["available"] is True
