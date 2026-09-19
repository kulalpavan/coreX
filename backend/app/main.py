from datetime import datetime
from typing import Any
from uuid import uuid4
import re

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .extraction import ExtractionError, process_report


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
    try:
        processed = process_report(payload, file.content_type, file.filename)
    except (ExtractionError, ValueError) as exc:
        raise HTTPException(422, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    reports[report_id] = {
        "id": report_id,
        "filename": file.filename or "untitled-report",
        "source_type": processed["source_type"],
        "ocr_confidence": processed["ocr_confidence"],
        "status": "pending_review",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "results": processed["results"],
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
