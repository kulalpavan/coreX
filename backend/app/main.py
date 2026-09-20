import dotenv
dotenv.load_dotenv()

from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4
import re
from io import BytesIO

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, model_validator
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .auth import (
    create_access_token,
    get_current_user_from_token,
    hash_password,
    security_scheme,
    verify_password,
)
from .explanations import explain_result
from .extraction import ExtractionError, process_report
from .clinical_chat import answer_question
from .guardrail import guardrail
from .ingestion import get_ocr_status, get_pdf_text_status
from .normalization import canonical_test_id
from .storage import ReportStore


DISCLAIMER = "Prototype education only. This summary is not a diagnosis. Discuss your results with a qualified clinician."
ALLOWED_TYPES = {"application/pdf", "image/jpeg", "image/png"}
MAX_BYTES = 15 * 1024 * 1024
DEFAULT_PATIENT_ID = "p_demo"


def _file_extension(filename: str | None, content_type: str | None) -> str:
    suffix = Path(filename or "").suffix.lower()
    if suffix in {".pdf", ".jpg", ".jpeg", ".png"}:
        return suffix
    return {"application/pdf": ".pdf", "image/jpeg": ".jpg", "image/png": ".png"}[content_type or ""]

app = FastAPI(title="Clarify Labs API", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

reports = ReportStore()


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme)) -> dict[str, Any]:
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=401,
            detail="Authentication token required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return get_current_user_from_token(credentials.credentials, reports)


class AuthCredentials(BaseModel):
    email: str
    password: str


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
    field_confidence: dict[str, float] | None = None
    review_required: bool = False
    user_corrected: bool = False
    explanation_text: str | None = None

    @model_validator(mode="after")
    def validate_result_fields(self) -> "TestResult":
        if not self.raw_test_name.strip():
            raise ValueError("raw_test_name cannot be empty")
        if self.reference_range_low is not None and self.reference_range_high is not None:
            if self.reference_range_low > self.reference_range_high:
                raise ValueError("reference_range_low cannot exceed reference_range_high")
        if self.report_date is not None:
            try:
                datetime.strptime(self.report_date, "%Y-%m-%d")
            except ValueError as error:
                raise ValueError("report_date must use YYYY-MM-DD format") from error
        if self.flag not in {None, "H", "L", "normal"}:
            raise ValueError("flag must be H, L, normal, or null")
        return self


class Confirmation(BaseModel):
    results: list[TestResult]


class ChatMessage(BaseModel):
    role: str = Field(pattern="^(user|model|assistant)$")
    content: str = Field(min_length=1, max_length=2000)

class ChatQuestion(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    history: list[ChatMessage] = Field(default_factory=list)


def canonicalize_test_name(raw_name: str) -> str:
    normalized = " ".join(raw_name.casefold().split())
    return canonical_test_id(normalized) or normalized.replace(" ", "_")


@app.get("/api/health")
def health() -> dict[str, Any]:
    ocr = get_ocr_status()
    pdf = get_pdf_text_status()
    return {
        "status": "ok",
        "ocr_available": ocr["available"],
        "tesseract_version": ocr["version"],
        "ocr_error": ocr["error"],
        "pdf_text_extraction_available": pdf["available"],
        "pdf_error": pdf["error"],
    }


# --- AUTH ENDPOINTS ---

@app.post("/api/auth/register")
def register(body: AuthCredentials) -> dict[str, Any]:
    email = body.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(400, "A valid email address is required.")
    if len(body.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters.")
    user_id = f"u_{uuid4().hex[:8]}"
    pwd_hash = hash_password(body.password)
    try:
        user = reports.create_user(user_id, email, pwd_hash)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    token = create_access_token(user["id"], user["email"])
    return {
        "user": {"id": user["id"], "email": user["email"]},
        "access_token": token,
        "token_type": "bearer",
    }


@app.post("/api/auth/login")
def login(body: AuthCredentials) -> dict[str, Any]:
    email = body.email.strip().lower()
    user = reports.get_user_by_email(email)
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(401, "Invalid email or password.")
    token = create_access_token(user["id"], user["email"])
    return {
        "user": {"id": user["id"], "email": user["email"]},
        "access_token": token,
        "token_type": "bearer",
    }


@app.get("/api/auth/me")
def me(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    return {"id": current_user["id"], "email": current_user["email"], "created_at": current_user["created_at"]}


@app.post("/api/auth/logout")
def logout() -> dict[str, str]:
    return {"status": "logged_out"}


# --- REPORT ENDPOINTS ---

@app.get("/api/reports")
def list_user_reports(current_user: dict[str, Any] = Depends(get_current_user)) -> list[dict[str, Any]]:
    user_reports = reports.list_for_user(current_user["id"])
    return [
        {
            "id": r["id"],
            "filename": r["filename"],
            "status": r["status"],
            "created_at": r.get("created_at"),
            "report_date": r.get("report_date"),
            "patient_id": r.get("patient_id"),
            "source_type": r.get("source_type"),
            "test_count": len(r.get("results", [])),
        }
        for r in user_reports
    ]


@app.post("/api/reports/upload")
async def upload_report(
    file: UploadFile = File(...),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, str]:
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
    reports.create({
        "id": report_id,
        "user_id": current_user["id"],
        "filename": file.filename or "untitled-report",
        "source_type": processed["source_type"],
        "content_type": file.content_type,
        "ocr_confidence": processed["ocr_confidence"],
        "extraction_provider": processed.get("extraction_provider", "deterministic"),
        "fallback_used": processed.get("fallback_used", False),
        "fallback_reason": processed.get("fallback_reason"),
        "raw_text": processed.get("raw_text", ""),
        "report_date": next((result.get("report_date") for result in processed["results"] if result.get("report_date")), None),
        "raw_file_path": str(reports.file_directory / f"{report_id}{_file_extension(file.filename, file.content_type)}"),
        "patient_id": DEFAULT_PATIENT_ID,
        "status": "pending_review",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "results": processed["results"],
    })
    Path(reports[report_id]["raw_file_path"]).write_bytes(payload)
    return {"report_id": report_id, "status": "processing"}


@app.get("/api/reports/{report_id}/extraction")
def get_extraction(
    report_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    report = reports.get_for_user(report_id, current_user["id"])
    if not report:
        raise HTTPException(404, "Report not found.")
    return {
        "report_id": report_id,
        "filename": report["filename"],
        "status": report["status"],
        "source_type": report["source_type"],
        "report_date": report.get("report_date"),
        "extraction_provider": report.get("extraction_provider", "deterministic"),
        "fallback_used": report.get("fallback_used", False),
        "fallback_reason": report.get("fallback_reason"),
        "results": report["results"],
    }


@app.get("/api/reports/{report_id}/source")
def get_source(
    report_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    report = reports.get_for_user(report_id, current_user["id"])
    if not report:
        raise HTTPException(404, "Report not found.")
    return {
        "report_id": report_id,
        "filename": report["filename"],
        "source_type": report["source_type"],
        "report_date": report.get("report_date"),
        "raw_text": report.get("raw_text", ""),
    }


@app.get("/api/reports/{report_id}/source-file")
def get_source_file(
    report_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> FileResponse:
    report = reports.get_for_user(report_id, current_user["id"])
    if not report:
        raise HTTPException(404, "Report not found.")
    source_path = Path(report.get("raw_file_path", ""))
    if not source_path.is_file():
        raise HTTPException(404, "The original report file is no longer available.")
    media_type = report.get("content_type", "application/octet-stream")
    return FileResponse(
        source_path,
        media_type=media_type,
        filename=report["filename"],
        content_disposition_type="inline",
    )


@app.post("/api/reports/{report_id}/confirm")
def confirm_report(
    report_id: str,
    body: Confirmation,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    report = reports.get_for_user(report_id, current_user["id"])
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
        result["explanation_text"] = guardrail(explain_result(result))
    report["status"] = "confirmed"
    reports.save(report)
    return {"report_id": report_id, "status": report["status"], "results": report["results"], "disclaimer": DISCLAIMER}


@app.get("/api/reports/{report_id}/explanations")
def get_explanations(
    report_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    report = reports.get_for_user(report_id, current_user["id"])
    if not report or report["status"] != "confirmed":
        raise HTTPException(409, "Confirm the report before viewing explanations.")
    return {"report_id": report_id, "results": report["results"], "disclaimer": DISCLAIMER}


@app.post("/api/reports/{report_id}/chat")
def chat_about_report(
    report_id: str,
    body: ChatQuestion,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    report = reports.get_for_user(report_id, current_user["id"])
    if not report or report["status"] != "confirmed":
        raise HTTPException(409, "Confirm the report before asking questions about it.")
    return answer_question(body.question, body.history, report)


@app.delete("/api/reports/{report_id}")
def delete_report(
    report_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, str]:
    deleted = reports.delete_for_user(report_id, current_user["id"])
    if not deleted:
        raise HTTPException(404, "Report not found.")
    return {"status": "deleted", "report_id": report_id}


@app.get("/api/patients/{patient_id}/trends/{canonical_test_id}")
def get_trend(
    patient_id: str,
    canonical_test_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    target_id = canonicalize_test_name(canonical_test_id)
    points = []
    for report in reports.values():
        if report.get("user_id") != current_user["id"] or report.get("patient_id") != patient_id or report.get("status") != "confirmed":
            continue
        for result in report.get("results", []):
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
def export_report(
    report_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> StreamingResponse:
    report = reports.get_for_user(report_id, current_user["id"])
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
        story.append(Paragraph(f"<b>{result['raw_test_name']}</b>: {result.get('explanation_text') or explain_result(result)}", styles["BodyText"]))
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
def delete_data(
    patient_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, str]:
    # Delete patient reports owned by current user
    user_reports = [r["id"] for r in reports.values() if r.get("user_id") == current_user["id"] and r.get("patient_id") == patient_id]
    for r_id in user_reports:
        del reports[r_id]
    return {"status": "deleted", "patient_id": patient_id}

