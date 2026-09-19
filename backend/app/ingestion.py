from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import os
import shutil


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


def evaluate_ocr_quality(text: str, confidence: float | None) -> float:
    if not text.strip() or confidence is None:
        return 0.0
        
    score = confidence * 0.4
    
    length = len(text)
    if length > 500:
        score += 0.1
    elif length > 100:
        score += 0.05
        
    lines = text.splitlines()
    line_count = len(lines)
    if line_count > 10:
        score += 0.1
    elif line_count > 3:
        score += 0.05
        
    word_count = len(text.split())
    if word_count > 50:
        score += 0.1
        
    try:
        from .extraction import extract_candidates
        candidates = extract_candidates(text, confidence)
        if len(candidates) > 2:
            score += 0.3
        elif len(candidates) > 0:
            score += 0.15
    except Exception:
        pass
        
    return min(1.0, score)


def _ocr_image_pass(image, strategy="fast") -> tuple[str, float | None]:
    try:
        import pytesseract
    except ImportError as exc:
        raise RuntimeError("Image OCR is currently unavailable. Please configure Tesseract or use a text-based PDF.") from exc

    try:
        from PIL import Image, ImageEnhance
    except ImportError as exc:
        raise RuntimeError("Image OCR is currently unavailable. Please configure Tesseract or use a text-based PDF.") from exc

    _configure_tesseract(pytesseract)
    
    image = image.convert("L")
    
    if strategy == "heavy":
        image = image.resize((image.width * 2, image.height * 2), Image.Resampling.LANCZOS)
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0)
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(2.0)
    else:
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.5)
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.5)
        
    try:
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    except pytesseract.TesseractNotFoundError as exc:
        raise RuntimeError("Image OCR is currently unavailable. Please configure Tesseract or use a text-based PDF.") from exc
        
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


def _ocr_image(image) -> tuple[str, float | None]:
    text_a, conf_a = _ocr_image_pass(image, strategy="fast")
    score_a = evaluate_ocr_quality(text_a, conf_a)
    
    if score_a >= 0.4:
        return text_a, conf_a
        
    text_b, conf_b = _ocr_image_pass(image, strategy="heavy")
    score_b = evaluate_ocr_quality(text_b, conf_b)
    
    if score_b > score_a:
        return text_b, conf_b
    return text_a, conf_a


def _ocr_payload(payload: bytes, source_type: str) -> tuple[str, float | None]:
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("Image OCR is currently unavailable. Please configure Tesseract or use a text-based PDF.") from exc

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
            return IngestionResult("", "pdf_scanned", confidence, "We couldn't reliably read enough text from this document. Please upload a clearer copy.")
        
        score = evaluate_ocr_quality(text, confidence)
        if score < 0.2:
            return IngestionResult("", "pdf_scanned", confidence, "We couldn't reliably read enough text from this image. Please upload a clearer photo with the entire report visible, good lighting, and minimal blur.")
            
        return IngestionResult(text, "pdf_scanned", confidence)

    text, confidence = _ocr_payload(payload, "image")
    if not text:
        return IngestionResult("", "image", confidence, "We couldn't reliably read enough text from this image. Please upload a clearer photo with the entire report visible, good lighting, and minimal blur.")
        
    score = evaluate_ocr_quality(text, confidence)
    if score < 0.2:
        return IngestionResult("", "image", confidence, "We couldn't reliably read enough text from this image. Please upload a clearer photo with the entire report visible, good lighting, and minimal blur.")
        
    return IngestionResult(text, "image", confidence)
