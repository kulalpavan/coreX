from __future__ import annotations

from datetime import date
import re
from typing import Any

from .ingestion import ingest_document
from .normalization import TEST_DICTIONARY, canonical_test_id, normalize_result


NUMBER = r"-?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?"
DATE_PATTERN = re.compile(r"\b(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})\b")
VALUE_PATTERN = re.compile(rf"(?P<value>{NUMBER})")
RANGE_PATTERN = re.compile(rf"(?P<low>{NUMBER})\s*(?:-|–|to)\s*(?P<high>{NUMBER})", re.I)
UPPER_RANGE_PATTERN = re.compile(rf"(?:<|<=)\s*(?P<high>{NUMBER})")
LOWER_RANGE_PATTERN = re.compile(rf"(?:>|>=)\s*(?P<low>{NUMBER})")
UNIT_PATTERN = re.compile(r"^[A-Za-zμµ/%^0-9]+(?:/[A-Za-zμµ0-9]+)?$")
FLAG_PATTERN = re.compile(r"\b(?P<flag>H|L|High|Low|Normal)\b", re.I)


class ExtractionError(ValueError):
    """Raised when a document has no safely extractable candidate rows."""


def process_report(payload: bytes, content_type: str | None, filename: str | None = None) -> dict[str, Any]:
    ingestion = ingest_document(payload, content_type, filename)
    if ingestion.error:
        raise ExtractionError(ingestion.error)
    from .extraction_adapter import extract_report_results_with_metadata

    extraction_run = extract_report_results_with_metadata(ingestion.text, ingestion.ocr_confidence)
    return {
        "raw_text": ingestion.text,
        "results": extraction_run.results,
        "extraction_provider": extraction_run.provider,
        "fallback_used": extraction_run.fallback_used,
        "fallback_reason": extraction_run.fallback_reason,
        "source_type": ingestion.source_type,
        "ocr_confidence": ingestion.ocr_confidence,
    }


def _number(value: str) -> float:
    if "," in value and "." not in value and len(value.rsplit(",", 1)[-1]) == 3:
        return float(value.replace(",", ""))
    return float(value.replace(",", "."))


def _known_test_prefix(line: str) -> tuple[str, str] | None:
    normalized = " ".join(line.replace("|", " ").split())
    names = sorted(
        (synonym for definition in TEST_DICTIONARY for synonym in definition.synonyms),
        key=len,
        reverse=True,
    )
    for name in names:
        # Allow leading non-alphanumeric characters (like stray punctuation from OCR)
        match = re.search(rf"^[^a-zA-Z0-9]*{re.escape(name)}(?=\s|$)", normalized, re.I)
        if match:
            return normalized[: match.end()].strip(), normalized[match.end() :].strip()
    return None


def _range_from_text(text: str) -> tuple[float | None, float | None, str]:
    match = RANGE_PATTERN.search(text)
    if match:
        return _number(match.group("low")), _number(match.group("high")), RANGE_PATTERN.sub(" ", text, count=1)
    match = UPPER_RANGE_PATTERN.search(text)
    if match:
        return None, _number(match.group("high")), UPPER_RANGE_PATTERN.sub(" ", text, count=1)
    match = LOWER_RANGE_PATTERN.search(text)
    if match:
        return _number(match.group("low")), None, LOWER_RANGE_PATTERN.sub(" ", text, count=1)
    return None, None, text


def _report_date(raw_text: str) -> str | None:
    match = DATE_PATTERN.search(raw_text)
    if not match:
        return None
    try:
        return date(int(match.group(1)), int(match.group(2)), int(match.group(3))).isoformat()
    except ValueError:
        return None


def _confidence(fields: dict[str, Any], line: str, ocr_confidence: float | None) -> tuple[float, dict[str, float]]:
    scores = {
        "raw_test_name": 0.85 if fields["raw_test_name"] else 0.0,
        "value": 0.9 if fields["value"] is not None else 0.15,
        "unit": 0.9 if fields["unit"] else 0.35,
        "reference_range": 0.9 if fields["reference_range_low"] is not None else 0.45,
        "flag": 0.9 if fields["flag"] else 0.65,
        "report_date": 0.9 if fields["report_date"] else 0.55,
    }
    if ocr_confidence is not None:
        for field in scores:
            scores[field] *= max(0.25, min(1.0, ocr_confidence))
    if len(line.split()) > 12:
        for field in scores:
            scores[field] *= 0.85
    confidence = sum(scores.values()) / len(scores)
    return round(max(0.0, min(1.0, confidence)), 3), {key: round(value, 3) for key, value in scores.items()}


def _parse_line(line: str, report_date: str | None, ocr_confidence: float | None) -> dict[str, Any] | None:
    line = " ".join(line.split()).strip(" |:")
    known_prefix = _known_test_prefix(line)
    if known_prefix is None:
        return None
    raw_name, remainder = known_prefix
    remainder = remainder.strip(" |:")
    missing_value_match = re.match(r"^(?P<name>[A-Za-z][A-Za-z0-9 /()%.-]{1,40}?)\s+(?:--|—|N/?A)\s+(?P<remainder>.+)$", line, re.I)
    if missing_value_match:
        remainder = missing_value_match.group("remainder")
        low, high, without_range = _range_from_text(remainder)
        unit_candidates = [token.strip("()[]") for token in without_range.split() if UNIT_PATTERN.fullmatch(token.strip("()[]"))]
        fields = {"raw_test_name": raw_name, "value": None, "unit": unit_candidates[0] if unit_candidates else None, "reference_range_low": low, "reference_range_high": high, "flag": None, "report_date": report_date}
        confidence, field_confidence = _confidence(fields, line, ocr_confidence)
        fields.update({"extraction_confidence": round(confidence * 0.5, 3), "field_confidence": field_confidence, "user_corrected": False})
        return normalize_result(fields)
    value_match = VALUE_PATTERN.match(remainder)
    if not value_match:
        return None
    value = _number(value_match.group("value"))
    remainder = remainder[value_match.end() :].strip(" |,;")
    low, high, without_range = _range_from_text(remainder)
    if low is not None and high is not None and low > high:
        low, high = high, low
        range_suspicious = True
    else:
        range_suspicious = False

    flag_match = FLAG_PATTERN.search(without_range)
    flag = flag_match.group("flag") if flag_match else None
    if flag:
        flag = "normal" if flag.casefold() == "normal" else ("H" if flag.casefold() in {"h", "high"} else "L")
    unit_candidates = [token.strip("()[]") for token in without_range.split() if UNIT_PATTERN.fullmatch(token.strip("()[]"))]
    unit = unit_candidates[0] if unit_candidates else None
    fields = {
        "raw_test_name": raw_name,
        "value": value,
        "unit": unit,
        "reference_range_low": low,
        "reference_range_high": high,
        "flag": flag,
        "report_date": report_date,
    }
    confidence, field_confidence = _confidence(fields, line, ocr_confidence)
    if range_suspicious or (value > 100000):
        confidence = round(confidence * 0.3, 3)
    fields.update(
        {
            "extraction_confidence": confidence,
            "field_confidence": field_confidence,
            "user_corrected": False,
        }
    )
    return normalize_result(fields)


def _parse_columnar_rows(raw_text: str, report_date: str | None, ocr_confidence: float | None) -> list[dict[str, Any]]:
    """Parse PDFs whose table extractor places each cell on its own line."""
    lines = [" ".join(line.split()).strip(" |:") for line in raw_text.splitlines()]
    results: list[dict[str, Any]] = []
    index = 0
    while index < len(lines):
        if _known_test_prefix(lines[index]) is None:
            index += 1
            continue
        row_parts = [lines[index]]
        lookahead = index + 1
        while lookahead < len(lines) and len(row_parts) < 6:
            if _known_test_prefix(lines[lookahead]) is not None:
                break
            if lines[lookahead]:
                row_parts.append(lines[lookahead])
            lookahead += 1
        candidate = _parse_line(" ".join(row_parts), report_date, ocr_confidence)
        if candidate:
            results.append(candidate)
        index = max(index + 1, lookahead)
    return results


def extract_candidates(raw_text: str, ocr_confidence: float | None = None) -> list[dict[str, Any]]:
    report_date = _report_date(raw_text)
    candidates: list[dict[str, Any]] = []
    for line in raw_text.splitlines():
        candidate = _parse_line(line, report_date, ocr_confidence)
        if candidate and not any(item["raw_test_name"] == candidate["raw_test_name"] for item in candidates):
            candidates.append(candidate)
    if not candidates:
        candidates = _parse_columnar_rows(raw_text, report_date, ocr_confidence)
    if not candidates:
        with open("failed_ocr.txt", "w", encoding="utf-8") as f:
            f.write(raw_text)
        raise ExtractionError("No recognizable laboratory results were found in the document.")
    for index, candidate in enumerate(candidates, 1):
        candidate["id"] = f"result_{index}"
    return candidates
