from datetime import datetime
from io import BytesIO

from fastapi.testclient import TestClient
from pypdf import PdfReader

from app.main import app, reports


client = TestClient(app)


def setup_function() -> None:
    reports.clear()


def confirmed_result(report_date: str, value: float, canonical_test_id: str = "hemoglobin") -> dict:
    return {
        "raw_test_name": "Hemoglobin",
        "canonical_test_id": canonical_test_id,
        "value": value,
        "unit": "g/dL",
        "reference_range_low": 12.0,
        "reference_range_high": 15.5,
        "flag": "normal",
        "report_date": report_date,
        "extraction_confidence": 0.95,
        "user_corrected": False,
    }


def create_report(report_date: str, value: float, status: str = "confirmed") -> str:
    report_id = f"r_{report_date.replace('-', '')}"
    reports[report_id] = {
        "id": report_id,
        "filename": f"report-{report_date}.png",
        "source_type": "image",
        "patient_id": "p_demo",
        "status": status,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "results": [confirmed_result(report_date, value)],
    }
    return report_id


def test_trends_include_only_confirmed_matching_results_in_date_order() -> None:
    create_report("2026-08-14", 13.8)
    create_report("2026-03-10", 14.2)
    create_report("2026-01-05", 12.9, status="pending_review")
    other_id = create_report("2026-04-10", 15.0)
    reports[other_id]["results"][0]["canonical_test_id"] = "tsh"

    response = client.get("/api/patients/p_demo/trends/hemoglobin")

    assert response.status_code == 200
    body = response.json()
    assert body["canonical_test_id"] == "hemoglobin"
    assert body["data"] == [
        {"date": "2026-03-10", "value": 14.2, "unit": "g/dL"},
        {"date": "2026-08-14", "value": 13.8, "unit": "g/dL"},
    ]
    assert "improv" not in body["trend_description"].lower()
    assert "worsen" not in body["trend_description"].lower()


def test_trends_report_insufficient_confirmed_data() -> None:
    create_report("2026-08-14", 13.8)

    response = client.get("/api/patients/p_demo/trends/hemoglobin")

    assert response.status_code == 200
    assert response.json()["data"] == []
    assert "not enough confirmed" in response.json()["trend_description"].lower()


def test_export_returns_readable_pdf_with_confirmed_content_and_disclaimer() -> None:
    report_id = create_report("2026-08-14", 13.8)
    reports[report_id]["results"][0]["explanation_text"] = "Hemoglobin is recorded as 13.8 g/dL. This is within the reported range."

    response = client.post(f"/api/reports/{report_id}/export")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    reader = PdfReader(BytesIO(response.content))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "Hemoglobin" in text
    assert "13.8" in text
    assert "Prototype education only" in text
    assert "attachment" in response.headers["content-disposition"]


def test_export_rejects_unconfirmed_report() -> None:
    report_id = create_report("2026-08-14", 13.8, status="pending_review")

    response = client.post(f"/api/reports/{report_id}/export")

    assert response.status_code == 409


def test_confirmation_rejects_invalid_reference_range() -> None:
    report_id = create_report("2026-08-14", 13.8, status="pending_review")
    invalid_result = confirmed_result("2026-08-14", 13.8) | {
        "reference_range_low": 16.0,
        "reference_range_high": 12.0,
    }

    response = client.post(f"/api/reports/{report_id}/confirm", json={"results": [invalid_result]})

    assert response.status_code == 422
    assert reports[report_id]["status"] == "pending_review"


def test_delete_data_is_scoped_to_requested_patient() -> None:
    own_report = create_report("2026-08-14", 13.8)
    other_report = create_report("2026-08-15", 14.1)
    reports[other_report]["patient_id"] = "p_other"

    response = client.delete("/api/patients/p_demo/data")

    assert response.status_code == 200
    assert own_report not in reports
    assert other_report in reports
