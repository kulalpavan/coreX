from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import os
import shutil


MIN_OCR_CONFIDENCE = 0.25


def _configure_tesseract(pytesseract) -> None:
    executable = shutil.which("tesseract")
    if not executable:
        candidates = (
            os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "Tesseract-OCR", "tesseract.exe"),
            os.path.join(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"), "Tesseract-OCR", "tesseract.exe"),
        )
        executable = next((candidate for candidate in candidates if os.path.isfile(candidate)), None)
    if executable:
        pytesseract.pytesseract.tesseract_cmd = executable


@dataclass
class IngestionResult:
    text: str
    source_type: str
    ocr_confidence: float | None
    error: str | None = None


def get_ocr_status() -> dict[str, str | bool | None]:
    """Report OCR readiness without making OCR a startup requirement."""
    try:
        import pytesseract
    except ImportError:
        return {"available": False, "version": None, "error": "pytesseract is not installed."}
    try:
        _configure_tesseract(pytesseract)
        version = str(pytesseract.get_tesseract_version()).splitlines()[0]
        return {"available": True, "version": version, "error": None}
    except Exception:
        return {
            "available": False,
            "version": None,
            "error": "Tesseract executable is not installed or is not on PATH.",
        }


def get_pdf_text_status() -> dict[str, str | bool | None]:
    try:
        import fitz  # noqa: F401
    except ImportError:
        return {"available": False, "error": "PyMuPDF is not installed."}
    return {"available": True, "error": None}


def classify_file(content_type: str | None, filename: str | None = None) -> str:
    if content_type == "application/pdf" or (filename or "").lower().endswith(".pdf"):
        return "pdf"
    if content_type == "image/jpeg" or (filename or "").lower().endswith((".jpg", ".jpeg")):
        return "image"
    if content_type == "image/png" or (filename or "").lower().endswith(".png"):
        return "image"
    raise ValueError("Unsupported file type. Upload a PDF, JPG, or PNG file.")


def _extract_pdf_text(payload: bytes) -> str:
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError("PDF processing is unavailable because PyMuPDF is not installed.") from exc

    try:
        document = fitz.open(stream=payload, filetype="pdf")
    except Exception as exc:
        raise ValueError("We couldn't read this PDF file. Please upload another copy.") from exc
    try:
        return "\n".join(page.get_text("text") for page in document).strip()
    finally:
        document.close()


def _ocr_image(image) -> tuple[str, float | None]:
    try:
        import pytesseract
    except ImportError as exc:
        raise RuntimeError("OCR is unavailable because pytesseract is not installed.") from exc

    try:
        from PIL import Image, ImageEnhance
    except ImportError as exc:
        raise RuntimeError("OCR is unavailable because Pillow is not installed.") from exc

    _configure_tesseract(pytesseract)
    
    # Pre-process for low quality images
    image = image.convert("L")
    
    # 1. Removed expensive upscaling that was causing major slowdowns
    
    # 2. Increase contrast moderately
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(1.5)
    
    # 3. Increase sharpness
    enhancer = ImageEnhance.Sharpness(image)
    image = enhancer.enhance(1.5)
    
    try:
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    except pytesseract.TesseractNotFoundError as exc:
        raise RuntimeError("OCR is unavailable because the Tesseract executable is not installed or is not on PATH.") from exc
    
    lines = []
    current_line = []
    last_tuple = None
    confidences = []
    
    for i in range(len(data["text"])):
        text = data["text"][i].strip()
        conf = float(data["conf"][i])
        if not text or conf < 0:
            continue
            
        current_tuple = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        if last_tuple is not None and current_tuple != last_tuple:
            if current_line:
                lines.append(" ".join(current_line))
                current_line = []
                
        current_line.append(text)
        confidences.append(conf)
        last_tuple = current_tuple
        
    if current_line:
        lines.append(" ".join(current_line))
        
    text_out = "\n".join(lines)
    confidence = (sum(confidences) / len(confidences) / 100) if confidences else None
    return text_out, confidence


def _ocr_payload(payload: bytes, source_type: str) -> tuple[str, float | None]:
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("OCR is unavailable because Pillow is not installed.") from exc

    if source_type == "image":
        return _ocr_image(Image.open(BytesIO(payload)))

    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError("Scanned PDF processing is unavailable because PyMuPDF is not installed.") from exc

    document = fitz.open(stream=payload, filetype="pdf")
    try:
        texts: list[str] = []
        confidences: list[float] = []
        for page in document:
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            text, confidence = _ocr_image(Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples))
            texts.append(text)
            if confidence is not None:
                confidences.append(confidence)
        return "\n".join(texts).strip(), (sum(confidences) / len(confidences) if confidences else None)
    finally:
        document.close()


def ingest_document(payload: bytes, content_type: str | None, filename: str | None = None) -> IngestionResult:
    file_kind = classify_file(content_type, filename)
    if not payload:
        return IngestionResult("", file_kind, None, "The uploaded document is empty.")

    if file_kind == "pdf":
        text = _extract_pdf_text(payload)
        if text:
            return IngestionResult(text, "pdf_text", None)
        text, confidence = _ocr_payload(payload, "pdf_scanned")
        if not text:
            return IngestionResult("", "pdf_scanned", confidence, "The PDF could not be read.")
        if confidence is not None and confidence < MIN_OCR_CONFIDENCE:
            return IngestionResult("", "pdf_scanned", confidence, "The scanned PDF was too unclear to read confidently. Please upload a clearer scan.")
        return IngestionResult(text, "pdf_scanned", confidence)

    text, confidence = _ocr_payload(payload, "image")
    if not text:
        return IngestionResult("", "image", confidence, "The image could not be read.")
    if confidence is not None and confidence < MIN_OCR_CONFIDENCE:
        return IngestionResult("", "image", confidence, "The image was too unclear to read confidently. Please upload a clearer scan.")
    return IngestionResult(text, "image", confidence)
