from io import BytesIO

from fastapi.testclient import TestClient
from pypdf import PdfReader
from reportlab.pdfgen import canvas

from app.main import app, reports


client = TestClient(app)
AUTH_HEADERS = {}


def setup_function() -> None:
    global AUTH_HEADERS
    reports.clear()
    reg_res = client.post("/api/auth/register", json={"email": "e2e_user@example.com", "password": "password123"})
    if reg_res.status_code == 200:
        data = reg_res.json()
        AUTH_HEADERS = {"Authorization": f"Bearer {data['access_token']}"}


def make_pdf(report_date: str, value: str) -> bytes:
    output = BytesIO()
    document = canvas.Canvas(output)
    text = document.beginText(40, 760)
    text.textLine(f"Report Date: {report_date}")
    text.textLine("Test Name | Result | Unit | Reference Range | Flag")
    text.textLine(f"Hemoglobin | {value} | g/dL | 12.0 - 15.5 | Normal")
    document.drawText(text)
    document.save()
    return output.getvalue()


def upload_and_confirm(report_date: str, value: str, corrected_value: float | None = None) -> str:
    upload = client.post(
        "/api/reports/upload",
        files={"file": (f"report-{report_date}.pdf", make_pdf(report_date, value), "application/pdf")},
        headers=AUTH_HEADERS,
    )
    assert upload.status_code == 200
    report_id = upload.json()["report_id"]
    extraction = client.get(f"/api/reports/{report_id}/extraction", headers=AUTH_HEADERS)
    assert extraction.status_code == 200
    source = client.get(f"/api/reports/{report_id}/source", headers=AUTH_HEADERS)
    source_file = client.get(f"/api/reports/{report_id}/source-file", headers=AUTH_HEADERS)
    assert source.status_code == 200
    assert "Hemoglobin" in source.json()["raw_text"]
    assert source_file.status_code == 200
    assert source_file.content.startswith(b"%PDF")
    results = extraction.json()["results"]
    if corrected_value is not None:
        results[0]["value"] = corrected_value
        results[0]["user_corrected"] = True
    confirmation = client.post(f"/api/reports/{report_id}/confirm", json={"results": results}, headers=AUTH_HEADERS)
    assert confirmation.status_code == 200
    return report_id


def test_upload_correct_confirm_explain_trend_export_and_delete() -> None:
    first_report = upload_and_confirm("2026-03-10", "13.1", corrected_value=13.4)
    second_report = upload_and_confirm("2026-08-14", "13.8")

    explanation = client.get(f"/api/reports/{first_report}/explanations", headers=AUTH_HEADERS)
    assert explanation.status_code == 200
    assert explanation.json()["results"][0]["value"] == 13.4
    assert "diagnos" not in explanation.json()["results"][0]["explanation_text"].lower()

    trend = client.get("/api/patients/p_demo/trends/hemoglobin", headers=AUTH_HEADERS)
    assert trend.status_code == 200
    assert [point["date"] for point in trend.json()["data"]] == ["2026-03-10", "2026-08-14"]
    assert [point["value"] for point in trend.json()["data"]] == [13.4, 13.8]

    exported = client.post(f"/api/reports/{second_report}/export", headers=AUTH_HEADERS)
    assert exported.status_code == 200
    assert exported.content.startswith(b"%PDF")
    pdf_text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(exported.content)).pages)
    assert "Hemoglobin" in pdf_text
    assert "Prototype education only" in pdf_text

    deleted = client.delete("/api/patients/p_demo/data", headers=AUTH_HEADERS)
    assert deleted.status_code == 200
    assert client.get(f"/api/reports/{first_report}/extraction", headers=AUTH_HEADERS).status_code == 404
    assert client.get(f"/api/reports/{second_report}/extraction", headers=AUTH_HEADERS).status_code == 404

