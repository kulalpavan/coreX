from datetime import date, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4
import re

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


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
    return f"{name} is recorded as {value:g} {unit}. The report does not include enough range information for a comparison. Discuss this result with your clinician for personal context."


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
    report["results"] = [item.model_dump() | {"id": item.id or f"result_{index}"} for index, item in enumerate(body.results, 1)]
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


@app.delete("/api/patients/{patient_id}/data")
def delete_data(patient_id: str) -> dict[str, str]:
    reports.clear()
    return {"status": "deleted", "patient_id": patient_id}
