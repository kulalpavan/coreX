from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import os
import shutil
import statistics


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
    """
    Extract text from a text-based PDF preserving table column order.

    Uses PyMuPDF word-level extraction with X-coordinate clustering so that
    multi-column tables (Test Name | Result | Unit | Reference Range) come out
    as proper rows rather than column-by-column streams.
    """
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError("PDF processing is unavailable because PyMuPDF is not installed.") from exc

    try:
        document = fitz.open(stream=payload, filetype="pdf")
    except Exception as exc:
        raise ValueError("We couldn't read this PDF file. Please upload another copy.") from exc

    try:
        page_texts: list[str] = []
        for page in document:
            # get_text("words") returns (x0, y0, x1, y1, word, block_no, line_no, word_no)
            words = page.get_text("words")
            if not words:
                page_texts.append("")
                continue

            # Group words by their Y-band using a sweep-line algorithm
            # Sort words by y0
            words.sort(key=lambda w: w[1])
            
            rows = []
            current_row = []
            current_y = None
            
            for w in words:
                x0, y0, x1, y1, word = w[0], w[1], w[2], w[3], w[4]
                if current_y is None:
                    current_y = y0
                    current_row.append((x0, x1, word))
                elif abs(y0 - current_y) <= 5:  # 5-pt tolerance
                    current_row.append((x0, x1, word))
                else:
                    rows.append(current_row)
                    current_row = [(x0, x1, word)]
                    current_y = y0
                    
            if current_row:
                rows.append(current_row)

            lines: list[str] = []
            for row in rows:
                # Sort words left→right within the row
                row.sort(key=lambda t: t[0])
                line_str = ""
                last_x1 = None
                last_char_width = 4.0 # default fallback
                
                for x0, x1, word in row:
                    char_width = max(1.0, (x1 - x0) / max(1, len(word)))
                    if last_x1 is not None:
                        gap = x0 - last_x1
                        if gap > char_width:
                            num_spaces = int(round(gap / char_width))
                            line_str += " " * min(40, num_spaces) # cap at 40 spaces to prevent huge gaps
                        else:
                            line_str += " "
                    line_str += word
                    last_x1 = x1
                    last_char_width = char_width
                    
                lines.append(line_str)

            page_texts.append("\n".join(lines))

        return "\n".join(page_texts).strip()
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
        # In fast mode, do not apply contrast enhancements.
        # Contrast enhancements often blow out lightly colored text, completely
        # destroying the result values in many medical reports.
        pass

    try:
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    except pytesseract.TesseractNotFoundError as exc:
        raise RuntimeError("Image OCR is currently unavailable. Please configure Tesseract or use a text-based PDF.") from exc

    # Reconstruct lines using positional bounding boxes
    # Each word has: left, top, width, height
    word_positions: list[tuple[float, float, str, float, float, float]] = []
    for i in range(len(data["text"])):
        text = data["text"][i].strip()
        conf = float(data["conf"][i])
        if not text or conf < 0:
            continue
        x0 = float(data["left"][i])
        y0 = float(data["top"][i])
        w = float(data["width"][i])
        h = float(data["height"][i])
        word_positions.append((x0, y0, text, conf, w, h))

    if not word_positions:
        return "", None

    # Calculate median height to use as a dynamic tolerance
    heights = [w[5] for w in word_positions]
    median_h = statistics.median(heights) if heights else 16.0
    
    # 0.4 * median_h prevents merging distinct rows while being robust to slight skew
    tolerance = max(8.0, median_h * 0.4)

    # Group words by their Y-band using a sweep-line algorithm
    # Use vertical center (y0 + h/2) for better grouping stability
    word_positions.sort(key=lambda t: t[1] + t[5] / 2.0)
    
    rows = []
    current_row = []
    current_y = None
    
    for w in word_positions:
        x0, y0, word, conf, width, h = w
        center_y = y0 + h / 2.0
        
        if current_y is None:
            current_y = center_y
            current_row.append((x0, word, width))
        elif abs(center_y - current_y) <= tolerance:
            current_row.append((x0, word, width))
            # Keep a rolling average/max of the Y center for this row to track slopes slightly
            current_y = (current_y * (len(current_row) - 1) + center_y) / len(current_row)
        else:
            rows.append(current_row)
            current_row = [(x0, word, width)]
            current_y = center_y
            
    if current_row:
        rows.append(current_row)

    lines: list[str] = []
    confidences = [wp[3] for wp in word_positions]
    
    char_width = max(4.0, median_h * 0.5)
    
    for row in rows:
        row.sort(key=lambda t: t[0])
        line_str = ""
        last_x1 = None
        
        for x0, word, width in row:
            if last_x1 is not None:
                gap = x0 - last_x1
                # If we have [digit] [.] [digit], reconstruct without spaces
                # This fixes cases where OCR detects decimal point but separates it
                is_decimal_seq = (word == "." and line_str and line_str[-1].isdigit()) or (line_str and line_str[-1] == "." and word and word[0].isdigit())
                
                if is_decimal_seq:
                    pass # Ignore gap, do not add space
                elif gap > char_width:
                    num_spaces = int(round(gap / char_width))
                    line_str += " " * min(40, num_spaces)
                else:
                    line_str += " "
            line_str += word
            last_x1 = x0 + width
            
        lines.append(line_str)

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
            text, confidence = _ocr_image(
                __import__("PIL").Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
            )
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
            return IngestionResult("", "pdf_scanned", confidence,
                                   "We couldn't reliably read enough text from this document. Please upload a clearer copy.")

        score = evaluate_ocr_quality(text, confidence)
        if score < 0.2:
            return IngestionResult("", "pdf_scanned", confidence,
                                   "We couldn't reliably read enough text from this image. Please upload a clearer photo with the entire report visible, good lighting, and minimal blur.")

        return IngestionResult(text, "pdf_scanned", confidence)

    text, confidence = _ocr_payload(payload, "image")
    if not text:
        return IngestionResult("", "image", confidence,
                               "We couldn't reliably read enough text from this image. Please upload a clearer photo with the entire report visible, good lighting, and minimal blur.")

    score = evaluate_ocr_quality(text, confidence)
    if score < 0.2:
        return IngestionResult("", "image", confidence,
                               "We couldn't reliably read enough text from this image. Please upload a clearer photo with the entire report visible, good lighting, and minimal blur.")

    return IngestionResult(text, "image", confidence)
