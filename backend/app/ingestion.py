from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO


MIN_OCR_CONFIDENCE = 0.25


@dataclass
class IngestionResult:
    text: str
    source_type: str
    ocr_confidence: float | None
    error: str | None = None


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

    document = fitz.open(stream=payload, filetype="pdf")
    try:
        return "\n".join(page.get_text("text") for page in document).strip()
    finally:
        document.close()


def _ocr_image(image) -> tuple[str, float | None]:
    try:
        import pytesseract
    except ImportError as exc:
        raise RuntimeError("OCR is unavailable because pytesseract is not installed.") from exc

    image = image.convert("L")
    image = image.point(lambda pixel: 255 if pixel > 180 else 0)
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    words = [text.strip() for text in data["text"] if text.strip()]
    confidences = [float(value) for value in data["conf"] if float(value) >= 0]
    confidence = (sum(confidences) / len(confidences) / 100) if confidences else None
    return " ".join(words), confidence


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
