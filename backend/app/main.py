from datetime import date, datetime
from typing import Any
from uuid import uuid4
import re
from io import BytesIO

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


DISCLAIMER = "Prototype education only. This summary is not a diagnosis. Discuss your results with a qualified clinician."
ALLOWED_TYPES = {"application/pdf", "image/jpeg", "image/png"}
MAX_BYTES = 15 * 1024 * 1024

app = FastAPI(title="Clarify Labs API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

reports: dict[str, dict[str, Any]] = {}


class TestResult(BaseModel):
    id: str | None = None
    raw_test_name: str
    canonical_test_id: str | None = None
    value: float | None = None
    unit: str | None = None
    reference_range_low: float | None = None
    reference_range_high: float | None = None
    flag: str | None = None
    report_date: str | None = None
    extraction_confidence: float = Field(ge=0, le=1)
    user_corrected: bool = False
    explanation_text: str | None = None


class Confirmation(BaseModel):
    results: list[TestResult]


def sample_results() -> list[dict[str, Any]]:
    rows = [
        ("Hemoglobin", 13.8, "g/dL", 12.0, 15.5, "normal", 0.97),
        ("Total Cholesterol", 214, "mg/dL", 0, 200, "H", 0.94),
        ("TSH", 2.4, "mIU/L", 0.4, 4.0, "normal", 0.88),
        ("ALT", 31, "U/L", 7, 56, "normal", 0.72),
    ]
    return [
        {
            "id": f"result_{index}",
            "raw_test_name": name,
            "canonical_test_id": canonicalize_test_name(name),
            "value": value,
            "unit": unit,
            "reference_range_low": low,
            "reference_range_high": high,
            "flag": flag,
            "report_date": "2026-08-14",
            "extraction_confidence": confidence,
            "user_corrected": False,
            "explanation_text": None,
        }
        for index, (name, value, unit, low, high, flag, confidence) in enumerate(rows, 1)
    ]


def extract_results(raw_text: str) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    pattern = re.compile(
        r"(?P<name>[A-Za-z][A-Za-z ]{2,})\s+(?P<value>-?\d+(?:\.\d+)?)\s+(?P<unit>[A-Za-z/%]+)"
    )
    for index, match in enumerate(pattern.finditer(raw_text), 1):
        matches.append(
            {
                "id": f"result_{index}",
                "raw_test_name": match.group("name").strip(),
                "canonical_test_id": canonicalize_test_name(match.group("name").strip()),
                "value": float(match.group("value")),
                "unit": match.group("unit"),
                "reference_range_low": None,
                "reference_range_high": None,
                "flag": None,
                "report_date": date.today().isoformat(),
                "extraction_confidence": 0.62,
                "user_corrected": False,
                "explanation_text": None,
            }
        )
    return matches or sample_results()


CANONICAL_TESTS = {
    "hemoglobin": "hemoglobin",
    "hb": "hemoglobin",
    "hgb": "hemoglobin",
    "total cholesterol": "total_cholesterol",
    "cholesterol": "total_cholesterol",
    "tsh": "tsh",
    "alt": "alt",
}


def canonicalize_test_name(raw_name: str) -> str:
    normalized = " ".join(raw_name.lower().split())
    return CANONICAL_TESTS.get(normalized, normalized.replace(" ", "_"))


def safe_explanation(result: dict[str, Any]) -> str:
    name = result["raw_test_name"]
    value = result.get("value")
    unit = result.get("unit") or ""
    low = result.get("reference_range_low")
    high = result.get("reference_range_high")
    if low is not None and high is not None and value is not None:
        position = "within" if low <= value <= high else "above" if value > high else "below"
        range_text = f"the reported range of {low:g}–{high:g} {unit}".strip()
        return f"{name} is a measurement recorded as {value:g} {unit}. This is {position} {range_text}. Discuss this result with your clinician for personal context."
    value_text = f"{value:g}" if isinstance(value, (int, float)) else "not available"
    return f"{name} is recorded as {value_text} {unit}. The report does not include enough range information for a comparison. Discuss this result with your clinician for personal context."


def guardrail(text: str) -> str:
    blocked = re.compile(r"\b(diagnos|disease|cancer|take|stop|medication|emergency|dangerous|cure)\w*\b", re.I)
    if blocked.search(text):
        return "This result is available for review. Discuss it with your clinician for personal context."
    return text


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/reports/upload")
async def upload_report(file: UploadFile = File(...)) -> dict[str, str]:
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, "Upload a PDF, JPG, or PNG file.")
    payload = await file.read()
    if len(payload) > MAX_BYTES:
        raise HTTPException(413, "Files must be 15 MB or smaller.")
    report_id = f"r_{uuid4().hex[:8]}"
    raw_text = payload.decode("utf-8", errors="ignore") if file.content_type != "application/pdf" else ""
    results = extract_results(raw_text)
    reports[report_id] = {
        "id": report_id,
        "filename": file.filename or "untitled-report",
        "source_type": "pdf_text" if file.content_type == "application/pdf" else "image",
        "patient_id": "p_demo",
        "status": "pending_review",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "results": results,
    }
    return {"report_id": report_id, "status": "processing"}


@app.get("/api/reports/{report_id}/extraction")
def get_extraction(report_id: str) -> dict[str, Any]:
    report = reports.get(report_id)
    if not report:
        raise HTTPException(404, "Report not found.")
    return {"report_id": report_id, "filename": report["filename"], "status": report["status"], "results": report["results"]}


@app.post("/api/reports/{report_id}/confirm")
def confirm_report(report_id: str, body: Confirmation) -> dict[str, Any]:
    report = reports.get(report_id)
    if not report:
        raise HTTPException(404, "Report not found.")
    report["results"] = [
        item.model_dump()
        | {
            "id": item.id or f"result_{index}",
            "canonical_test_id": item.canonical_test_id or canonicalize_test_name(item.raw_test_name),
        }
        for index, item in enumerate(body.results, 1)
    ]
    for result in report["results"]:
        result["explanation_text"] = guardrail(safe_explanation(result))
    report["status"] = "confirmed"
    return {"report_id": report_id, "status": report["status"], "results": report["results"], "disclaimer": DISCLAIMER}


@app.get("/api/reports/{report_id}/explanations")
def get_explanations(report_id: str) -> dict[str, Any]:
    report = reports.get(report_id)
    if not report or report["status"] != "confirmed":
        raise HTTPException(409, "Confirm the report before viewing explanations.")
    return {"report_id": report_id, "results": report["results"], "disclaimer": DISCLAIMER}


@app.get("/api/patients/{patient_id}/trends/{canonical_test_id}")
def get_trend(patient_id: str, canonical_test_id: str) -> dict[str, Any]:
    target_id = canonicalize_test_name(canonical_test_id)
    points = []
    for report in reports.values():
        if report["patient_id"] != patient_id or report["status"] != "confirmed":
            continue
        for result in report["results"]:
            result_id = result.get("canonical_test_id") or canonicalize_test_name(result["raw_test_name"])
            if result_id.lower() != target_id or result.get("value") is None or not result.get("report_date"):
                continue
            points.append(
                {
                    "date": result["report_date"],
                    "value": result["value"],
                    "unit": result.get("unit") or "",
                    "flag": result.get("flag"),
                }
            )
    points.sort(key=lambda point: point["date"])
    has_sufficient_data = len(points) >= 2
    data = [{"date": point["date"], "value": point["value"], "unit": point["unit"]} for point in points] if has_sufficient_data else []
    if not has_sufficient_data:
        description = "Not enough confirmed data points are available for this test."
    else:
        description = f"This value moved from {data[0]['value']} {data[0]['unit']} on {data[0]['date']} to {data[-1]['value']} {data[-1]['unit']} on {data[-1]['date']}."
    return {
        "canonical_test_id": target_id,
        "data": data,
        "trend_description": description,
        "points": points if has_sufficient_data else [],
        "description": description,
    }


def _pdf_value(value: Any) -> str:
    return "Not available" if value is None else str(value)


def _draw_disclaimer(canvas: Any, document: Any) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#795e49"))
    canvas.drawString(document.leftMargin, 0.45 * inch, DISCLAIMER)
    canvas.setStrokeColor(colors.HexColor("#d5c9b8"))
    canvas.line(document.leftMargin, 0.62 * inch, letter[0] - document.rightMargin, 0.62 * inch)
    canvas.restoreState()


@app.post("/api/reports/{report_id}/export")
def export_report(report_id: str) -> StreamingResponse:
    report = reports.get(report_id)
    if not report:
        raise HTTPException(404, "Report not found.")
    if report["status"] != "confirmed":
        raise HTTPException(409, "Confirm the report before exporting it.")

    styles = getSampleStyleSheet()
    story = [
        Paragraph("Clarify Labs Patient Summary", styles["Title"]),
        Paragraph(f"Report: {report['filename']}", styles["Normal"]),
        Paragraph(f"Patient profile: {report['patient_id']}", styles["Normal"]),
        Spacer(1, 0.2 * inch),
    ]
    table_data = [["Test", "Value", "Unit", "Reference range", "Flag"]]
    for result in report["results"]:
        low = _pdf_value(result.get("reference_range_low"))
        high = _pdf_value(result.get("reference_range_high"))
        table_data.append(
            [
                result["raw_test_name"],
                _pdf_value(result.get("value")),
                _pdf_value(result.get("unit")),
                f"{low} - {high}",
                _pdf_value(result.get("flag")),
            ]
        )
    table = Table(table_data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#155c51")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d9d7d1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f0eb")]),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 0.25 * inch))
    story.append(Paragraph("Plain-language explanations", styles["Heading2"]))
    for result in report["results"]:
        story.append(Paragraph(f"<b>{result['raw_test_name']}</b>: {result.get('explanation_text') or safe_explanation(result)}", styles["BodyText"]))
        story.append(Spacer(1, 0.1 * inch))

    output = BytesIO()
    document = SimpleDocTemplate(output, pagesize=letter, bottomMargin=0.85 * inch)
    document.build(story, onFirstPage=_draw_disclaimer, onLaterPages=_draw_disclaimer)
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="clarify-labs-{report_id}.pdf"'},
    )


@app.delete("/api/patients/{patient_id}/data")
def delete_data(patient_id: str) -> dict[str, str]:
    reports.clear()
    return {"status": "deleted", "patient_id": patient_id}
