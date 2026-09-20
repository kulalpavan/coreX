from __future__ import annotations

from datetime import date
import re
from typing import Any

from .ingestion import ingest_document
from .normalization import TEST_DICTIONARY, canonical_test_id, normalize_result, reference_range_for


# ── Number patterns ───────────────────────────────────────────────────────────
NUMBER = r"-?(?:\d{1,3}(?:,\d{2,3})+|\d+)(?:\.\d+)?"
DATE_PATTERN = re.compile(r"\b(20\d{2})[-/.](0?[1-9]|1[0-2])[-/.](0?[1-9]|[12]\d|3[01])\b")

# Range: low - high  OR  low to high
RANGE_PATTERN = re.compile(rf"(?P<low>{NUMBER})\s*[-=~–]+\s*(?P<high>{NUMBER})", re.I)
# Single-bound ranges: < 200  or  > 40
UPPER_RANGE_PATTERN = re.compile(rf"(?:<|<=|upto|up to)\s*(?P<high>{NUMBER})", re.I)
LOWER_RANGE_PATTERN = re.compile(rf"(?:>|>=)\s*(?P<low>{NUMBER})", re.I)

# Unit: e.g. g/dL, mg/dL, %, cells/µL, fL, pg, mIU/mL, U/L
UNIT_PATTERN = re.compile(r"^[A-Za-zÃµµ/%^0-9.\[\]×]+(?:[/×][A-Za-zÃµµ0-9.³²]+)*$")

# Flag — only standalone words not part of unit abbreviations
FLAG_PATTERN = re.compile(r"(?<![/A-Za-z0-9])(?P<flag>High|Low|Normal|\bH\b|\bL\b)", re.I)

# Generic row: [TestName] [Value] [Rest...]
GENERIC_ROW_PATTERN = re.compile(
    r"^(?P<name>[A-Za-z][A-Za-z0-9 \-()/.,]{2,50}?)\s+"
    rf"(?P<value>{NUMBER})\s+"
    r"(?P<remainder>.+)$"
)

# ── Known OCR artefacts: some scanners drop decimals ─────────────────────────
# Maps (canonical_test_id, likely_wrong_int) -> correct_float
# Used to detect and fix OCR decimal-drop errors
_OCR_VALUE_CORRECTIONS: dict[str, dict[str, Any]] = {
    "hematocrit":       {"threshold": 100.0, "scale": 10.0, "reason": "Hematocrit > 100% is biologically impossible; OCR dropped decimal"},
    "albumin":          {"threshold": 10.0,  "scale": 10.0, "reason": "Albumin > 10 g/dL is biologically impossible; OCR dropped decimal"},
    "globulin":         {"threshold": 10.0,  "scale": 10.0, "reason": "Globulin > 10 g/dL is biologically impossible; OCR dropped decimal"},
    "total_protein":    {"threshold": 15.0,  "scale": 10.0, "reason": "Total protein > 15 g/dL is biologically impossible; OCR dropped decimal"},
    "creatinine":       {"threshold": 15.0,  "scale": 10.0, "reason": "Creatinine > 15 mg/dL is extremely rare; OCR dropped decimal"},
    "hba1c":            {"threshold": 25.0,  "scale": 10.0, "reason": "HbA1c > 25% is biologically impossible; OCR dropped decimal"},
    "tsh":              {"threshold": 100.0, "scale": 10.0, "reason": "TSH > 100 is possible but if raw is integer it's likely a dropped decimal"},
    "free_t4":          {"threshold": 10.0,  "scale": 10.0, "reason": "Free T4 > 10 ng/dL is biologically impossible; OCR dropped decimal"},
    "free_t3":          {"threshold": 20.0,  "scale": 10.0, "reason": "Free T3 > 20 pg/mL is biologically impossible; OCR dropped decimal"},
    "ag_ratio":         {"threshold": 10.0,  "scale": 10.0, "reason": "A/G ratio > 10 is biologically impossible; OCR dropped decimal"},
    "direct_bilirubin": {"threshold": 5.0,   "scale": 10.0, "reason": "Direct Bilirubin > 5 mg/dL without decimal is likely dropped decimal"},
    "total_bilirubin":  {"threshold": 15.0,  "scale": 10.0, "reason": "Total Bilirubin > 15 mg/dL without decimal is likely dropped decimal"},
    "mcv":              {"threshold": 200.0, "scale": 10.0, "reason": "MCV > 200 fL is biologically impossible; OCR dropped decimal"},
    "mch":              {"threshold": 100.0, "scale": 10.0, "reason": "MCH > 100 pg is biologically impossible; OCR dropped decimal"},
    "mchc":             {"threshold": 100.0, "scale": 10.0, "reason": "MCHC > 100 g/dL is biologically impossible; OCR dropped decimal"},
}


class ExtractionError(ValueError):
    """Raised when a document has no safely extractable candidate rows."""


def process_report(payload: bytes, content_type: str | None, filename: str | None = None) -> dict[str, Any]:
    ingestion = ingest_document(payload, content_type, filename)
    if ingestion.error:
        raise ExtractionError(ingestion.error)
    from .extraction_adapter import extract_report_results_with_metadata

    extraction_run = extract_report_results_with_metadata(ingestion.text, ingestion.ocr_confidence)

    results = extraction_run.results
    rows_extracted = len(results)
    rows_needing_review = sum(1 for r in results if r.get("extraction_confidence", 1.0) < 0.6)
    status = "SUCCESS"
    if rows_extracted == 0:
        status = "FAILURE"
    elif rows_needing_review > 0:
        status = "PARTIAL_SUCCESS"

    return {
        "raw_text": ingestion.text,
        "results": results,
        "extraction_provider": extraction_run.provider,
        "fallback_used": extraction_run.fallback_used,
        "fallback_reason": extraction_run.fallback_reason,
        "source_type": ingestion.source_type,
        "ocr_confidence": ingestion.ocr_confidence,
        "status": status,
        "rows_extracted": rows_extracted,
        "rows_needing_review": rows_needing_review,
    }


def _number(value: str) -> float:
    """Parse a number string, handling comma-as-thousands or comma-as-decimal."""
    if "," in value and "." not in value and len(value.rsplit(",", 1)[-1]) == 3:
        return float(value.replace(",", ""))
    return float(value.replace(",", "."))


def _normalize_unit(raw: str) -> str:
    """Normalise common OCR unit mis-reads to a canonical form."""
    mappings = {
        "iu": "cells/µL",  # WBC OCR artefact
        "lu": "cells/µL",
        "cells/ul": "cells/µL",
        "cells/µl": "cells/µL",
        "g/dl": "g/dL",
        "g/dl.": "g/dL",
        "mg/dl": "mg/dL",
        "mg/dl.": "mg/dL",
        "mg/dl,": "mg/dL",
        "fdl": "g/dL",
        "fdl.": "g/dL",
        "fakh/pl": "lakh/µL",   # OCR for lakh
        "lakh/ul": "lakh/µL",
        "million/ul": "million/µL",
        "million/ul.": "million/µL",
        "miu/ml": "µIU/mL",
        "uiu/ml": "µIU/mL",
        "u/l": "U/L",
        "u/l.": "U/L",
        "ml/min/1.73m?": "mL/min/1.73m²",
        "ml/min/1.73m2": "mL/min/1.73m²",
        "e": None,   # standalone 'e' is not a unit
    }
    return mappings.get(raw.casefold().strip("."), raw)


def _correct_ocr_value(value: float, value_str: str, canonical_id: str | None, ref_low: float | None, ref_high: float | None) -> tuple[float, bool, str | None, bool]:
    """
    Detect and correct OCR decimal-drop artefacts strictly based on biological impossibilities.
    Returns: (corrected_value, was_corrected, reason, review_required)
    """
    if canonical_id is None or value is None:
        return value, False, None, False

    # Never run decimal correction on a value that already contains a decimal point
    if "." in value_str:
        return value, False, None, False

    value_str_clean = value_str.strip()
    if value_str_clean.startswith("0") and len(value_str_clean) > 1 and "." not in value_str_clean and not value_str_clean.startswith("0,"):
        corrected_str = "0." + value_str_clean[1:]
        try:
            corrected = float(corrected_str)
            return corrected, True, f"OCR dropped decimal: leading zero indicates fraction ({corrected_str})", True
        except ValueError:
            pass

    # 1. Very specific tests where certain integer values are biologically impossible
    if canonical_id in _OCR_VALUE_CORRECTIONS:
        rule = _OCR_VALUE_CORRECTIONS[canonical_id]
        if value >= rule["threshold"]:
            corrected = round(value / rule["scale"], 3)
            return corrected, True, rule["reason"], True

    # 2. If the value isn't biologically impossible (or no rule exists),
    # but it's an integer that falls suspiciously outside the reference range
    # while its divided-by-10 counterpart would fit perfectly, we mark it for review
    # but DO NOT blindly invent a decimal point.
    review_required = False
    if ref_low is not None and ref_high is not None and ref_high > 0:
        if value > ref_high * 1.5:
            candidate = value / 10.0
            if (ref_low / 2.0) <= candidate <= (ref_high * 1.5):
                review_required = True

    # Legitimate integers (e.g. 22) that don't violate biological limits will remain unchanged here
    return value, False, None, review_required


def _known_test_prefix(line: str) -> tuple[str, str] | None:
    """Try to find a known test name at the start of the line (Strategy 1)."""
    normalized = " ".join(line.replace("|", " ").split())
    # Sort longest synonyms first so "Mean Corpuscular Hemoglobin Concentration" beats "Mean Corpuscular Hemoglobin"
    names = sorted(
        (synonym for definition in TEST_DICTIONARY for synonym in definition.synonyms),
        key=len,
        reverse=True,
    )
    for name in names:
        match = re.search(rf"^[^a-zA-Z0-9]*{re.escape(name)}(?=\s|$|,|:|\|)", normalized, re.I)
        if match:
            return normalized[: match.end()].strip(), normalized[match.end():].strip()
    return None


def _range_from_text(text: str) -> tuple[float | None, float | None, str]:
    """Extract (low, high, text_without_range) from a string."""
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
    """Extract the first valid date from the text."""
    # Prefer Indian format: 15 Mar 2024
    indian = re.search(
        r"\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(20\d{2})\b",
        raw_text, re.I,
    )
    if indian:
        month_map = {m: i for i, m in enumerate(
            ["jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec"], 1)}
        try:
            d = date(int(indian.group(3)), month_map[indian.group(2).lower()[:3]], int(indian.group(1)))
            return d.isoformat()
        except ValueError:
            pass
    match = DATE_PATTERN.search(raw_text)
    if match:
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3))).isoformat()
        except ValueError:
            return None
    return None


def _confidence(
    fields: dict[str, Any],
    line: str,
    ocr_confidence: float | None,
    range_from_kb: bool = False,
) -> tuple[float, dict[str, float]]:
    """Compute extraction confidence. range_from_kb=True means we filled range from knowledge base."""
    scores = {
        "raw_test_name": 0.90 if fields["raw_test_name"] else 0.0,
        "value":          0.92 if fields["value"] is not None else 0.15,
        "unit":           0.85 if fields["unit"] else 0.35,
        "reference_range": 0.85 if fields["reference_range_low"] is not None or fields["reference_range_high"] is not None else (0.75 if range_from_kb else 0.45),
        "flag":           0.80 if fields["flag"] else 0.70,
        "report_date":    0.85 if fields["report_date"] else 0.60,
    }
    if ocr_confidence is not None:
        scale = max(0.3, min(1.0, ocr_confidence))
        for field in scores:
            scores[field] *= scale
    if len(line.split()) > 14:
        for field in scores:
            scores[field] *= 0.85
    confidence = sum(scores.values()) / len(scores)
    return round(max(0.0, min(1.0, confidence)), 3), {k: round(v, 3) for k, v in scores.items()}


def _build_result(
    raw_name: str,
    value: float | None,
    value_str: str | None,
    remainder: str,
    line: str,
    report_date: str | None,
    ocr_confidence: float | None,
    strategy: int,
) -> dict[str, Any]:
    low, high, without_range = _range_from_text(remainder)

    range_suspicious = False
    if low is not None and high is not None and low > high:
        low, high = high, low
        range_suspicious = True

    # ── Unit extraction ──
    unit_candidates = [
        token.strip("()[].,")
        for token in without_range.split()
        if UNIT_PATTERN.fullmatch(token.strip("()[].,"))
        and len(token.strip("()[].,")) >= 1
        and not token.strip("()[].,").isnumeric()
    ]
    raw_unit = unit_candidates[0] if unit_candidates else None
    unit = _normalize_unit(raw_unit) if raw_unit else None

    # ── Flag extraction (after removing unit text to avoid false L in U/L) ──
    without_unit_text = without_range
    if raw_unit:
        without_unit_text = re.sub(r"\b" + re.escape(raw_unit) + r"\b", " ", without_range)
    flag_match = FLAG_PATTERN.search(without_unit_text)
    flag = flag_match.group("flag") if flag_match else None
    if flag:
        flag = "normal" if flag.casefold() == "normal" else ("H" if flag.casefold() in {"h", "high"} else "L")

    # ── OCR lakh/million unit tolerance ──
    remainder_lower = remainder.casefold()
    if "lakh" in remainder_lower:
        unit = "lakh/µL"
    elif "million" in remainder_lower:
        unit = "million/µL"

    # Determine canonical_id now so we can use it for OCR correction
    c_id = canonical_test_id(raw_name)

    # Use KB range for correction heuristic if document range is missing
    eff_low, eff_high = low, high
    if eff_low is None and eff_high is None and c_id:
        kb_ranges = reference_range_for(c_id)
        if kb_ranges:
            eff_low, eff_high = kb_ranges

    # ── OCR decimal-drop correction ──
    ocr_corrected = False
    review_required = False
    correction_reason = None
    original_ocr_value = value_str

    if value is not None and value_str is not None:
        value, ocr_corrected, correction_reason, review_required = _correct_ocr_value(value, value_str, c_id, eff_low, eff_high)

    # Build fields dict (range may still be None — normalize_result fills from knowledge base)
    fields = {
        "raw_test_name": raw_name,
        "value": value,
        "unit": unit,
        "reference_range_low": low,
        "reference_range_high": high,
        "flag": flag,
        "report_date": report_date,
    }
    
    if review_required or ocr_corrected:
        fields["review_required"] = True
    if ocr_corrected:
        fields["correction_reason"] = correction_reason
        fields["original_ocr_value"] = original_ocr_value

    # Check if range will be filled from knowledge base
    range_from_kb = (low is None and high is None and c_id is not None)

    confidence, field_confidence = _confidence(fields, line, ocr_confidence, range_from_kb=range_from_kb)

    if range_suspicious:
        confidence = round(confidence * 0.5, 3)
    if value is not None and value > 100000 and c_id not in ("white_blood_cell_count", "platelet_count", "red_blood_cell_count"):
        confidence = round(confidence * 0.3, 3)
    if ocr_corrected:
        confidence = round(confidence * 0.85, 3)
        field_confidence["value"] = round(field_confidence.get("value", 0.5) * 0.85, 3)
    if strategy == 2:
        confidence = round(confidence * 0.85, 3)
        field_confidence["raw_test_name"] = round(field_confidence.get("raw_test_name", 0.5) * 0.85, 3)
    # OCR: leading zero on integer (e.g. "08") → low confidence
    if value_str and value_str.startswith("0") and len(value_str) > 1 and "." not in value_str:
        field_confidence["value"] = round(field_confidence.get("value", 0.5) * 0.5, 3)
        confidence = round(confidence * 0.75, 3)

    fields.update({
        "extraction_confidence": confidence,
        "field_confidence": field_confidence,
        "user_corrected": False,
    })

    return normalize_result(fields)


def _parse_table_row(line: str, report_date: str | None, ocr_confidence: float | None) -> dict[str, Any] | None:
    columns = [col.strip(" |:") for col in re.split(r'\s{2,}', line) if col.strip(" |:")]
    if len(columns) < 2:
        return None
    
    raw_name = columns[0]
    if not _known_test_prefix(raw_name) and not GENERIC_ROW_PATTERN.match(f"{raw_name} 1"):
        return None
        
    value_str = None
    value = None
    remainder_cols = columns[1:]
    
    val_match = re.search(rf"^(?P<value>{NUMBER})$", remainder_cols[0])
    if val_match:
        value_str = val_match.group("value")
        value = _number(value_str)
        remainder = " ".join(remainder_cols[1:])
    else:
        val_match = re.search(rf"^(?P<value>{NUMBER})", remainder_cols[0])
        if val_match:
            value_str = val_match.group("value")
            value = _number(value_str)
            rem = []
            if remainder_cols[0][val_match.end():].strip():
                rem.append(remainder_cols[0][val_match.end():].strip())
            rem.extend(remainder_cols[1:])
            remainder = " ".join(rem)
        else:
            value_str = None
            value = None
            remainder = " ".join(remainder_cols)
            
    return _build_result(raw_name, value, value_str, remainder, line, report_date, ocr_confidence, strategy=3)


def _parse_line(line: str, report_date: str | None, ocr_confidence: float | None) -> dict[str, Any] | None:
    line = " ".join(line.split()).strip(" |:")

    # ── Strategy 1: Dictionary-aware ─────────────────────────────────────────
    known_prefix = _known_test_prefix(line)
    if known_prefix:
        raw_name, remainder = known_prefix
        remainder = remainder.strip(" |:")

        # Explicit missing value markers
        missing_match = re.match(r"^(?:--|N/?A|NA)\s+(?P<remainder>.+)$", remainder, re.I)
        if missing_match:
            return _build_result(raw_name, None, None, missing_match.group("remainder"),
                                 line, report_date, ocr_confidence, strategy=1)

        value_match = re.search(rf"(?P<value>{NUMBER})", remainder)
        if value_match:
            value_str = value_match.group("value")
            value = _number(value_str)
            remainder = remainder[value_match.end():].strip(" |,;")
            return _build_result(raw_name, value, value_str, remainder, line, report_date, ocr_confidence, strategy=1)

        # Test name found but NO value on this line — return None so the
        # columnar parser can join subsequent lines (value, unit, range)
        return None

    # ── Strategy 2: Generic row pattern ──────────────────────────────────────
    generic_match = GENERIC_ROW_PATTERN.match(line)
    if generic_match:
        raw_name = generic_match.group("name").strip(" |:-")
        value_str = generic_match.group("value")
        value = _number(value_str)
        remainder = generic_match.group("remainder").strip(" |,;")
        if len(raw_name) > 2 and not raw_name.isnumeric() and re.search(r"[A-Za-z]", raw_name):
            return _build_result(raw_name, value, value_str, remainder, line, report_date, ocr_confidence, strategy=2)

    return None


def _parse_columnar_rows(raw_text: str, report_date: str | None, ocr_confidence: float | None) -> list[dict[str, Any]]:
    """
    Parse reports where each table cell occupies its own line.
    Groups lines belonging to the same test row together before parsing.
    """
    lines = [line.strip(" |:") for line in raw_text.splitlines()]
    results: list[dict[str, Any]] = []
    index = 0
    while index < len(lines):
        # We allow a little bit of spacing at the start, but we want to check if it's a known prefix.
        norm_line = " ".join(lines[index].split())
        if not norm_line or _known_test_prefix(norm_line) is None:
            index += 1
            continue
            
        # Collect following non-test lines as continuation of this row (up to 6 total parts)
        row_parts = [lines[index].strip()]
        lookahead = index + 1
        while lookahead < len(lines) and len(row_parts) < 6:
            norm_lookahead = " ".join(lines[lookahead].split())
            if norm_lookahead and _known_test_prefix(norm_lookahead) is not None:
                break
            if lines[lookahead].strip():
                row_parts.append(lines[lookahead].strip())
            lookahead += 1
            
        joined_row = "  ".join(row_parts)
        candidate = None
        if re.search(r'\s{2,}', joined_row):
            candidate = _parse_table_row(joined_row, report_date, ocr_confidence)
        if not candidate:
            candidate = _parse_line(joined_row, report_date, ocr_confidence)
            
        if candidate:
            results.append(candidate)
        index = max(index + 1, lookahead)
    return results


def _deduplicate(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Remove duplicates: prefer the candidate with higher extraction_confidence.
    Dedup key is the canonical_test_id if available, else the normalised raw name.
    """
    seen: dict[str, dict[str, Any]] = {}
    for item in candidates:
        key = (item.get("canonical_test_id") or " ".join(item["raw_test_name"].casefold().split()))
        existing = seen.get(key)
        if existing is None or item.get("extraction_confidence", 0) > existing.get("extraction_confidence", 0):
            seen[key] = item
    return list(seen.values())


def extract_candidates(raw_text: str, ocr_confidence: float | None = None) -> list[dict[str, Any]]:
    report_date = _report_date(raw_text)
    candidates: list[dict[str, Any]] = []

    lines = raw_text.splitlines()
    for i, line in enumerate(lines):
        candidate = None
        if re.search(r'\s{2,}', line):
            candidate = _parse_table_row(line, report_date, ocr_confidence)
            
        if not candidate:
            candidate = _parse_line(line, report_date, ocr_confidence)
            
        # Multi-line column-aware association (if value is missing but next line has numbers matching the column)
        if candidate and candidate.get("value") is None and i + 1 < len(lines):
            # Check if next line contains a number that vertically aligns with the gap between test name and unit
            next_line = lines[i + 1]
            
            # Find all numbers on the next line and their X coordinates (string indices)
            for m in re.finditer(NUMBER, next_line):
                num_val_str = m.group()
                num_start = m.start()
                
                # Check alignment: Test name ends around index X, unit starts around index Y.
                name_match = re.search(re.escape(candidate["raw_test_name"]), line)
                unit_match = re.search(re.escape(candidate.get("unit") or ""), line) if candidate.get("unit") else None
                
                name_end = name_match.end() if name_match else 0
                unit_start = unit_match.start() if unit_match else len(line)
                
                # If the number is roughly between the test name and the unit, associate it!
                if name_end - 5 <= num_start <= unit_start + 15:
                    candidate["value"] = _number(num_val_str)
                    
                    # Search for ranges on the same next line
                    range_match = RANGE_PATTERN.search(next_line[m.end():])
                    if range_match:
                        candidate["reference_range_low"] = _number(range_match.group("low"))
                        candidate["reference_range_high"] = _number(range_match.group("high"))
                    
                    # Validate the newly assigned value to see if it needs decimal correction
                    c_id = candidate.get("canonical_test_id")
                    if c_id:
                        eff_low = candidate.get("reference_range_low")
                        eff_high = candidate.get("reference_range_high")
                        if eff_low is None and eff_high is None and c_id:
                            kb_ranges = reference_range_for(c_id)
                            if kb_ranges:
                                eff_low, eff_high = kb_ranges

                        corr_val, ocr_corr, correction_reason, review_req = _correct_ocr_value(
                            candidate["value"], 
                            num_val_str,
                            c_id, 
                            eff_low, 
                            eff_high
                        )
                        if review_req or ocr_corr:
                            candidate["review_required"] = True
                        if ocr_corr:
                            candidate["value"] = corr_val
                            candidate["correction_reason"] = correction_reason
                            candidate["original_ocr_value"] = num_val_str
                            
                    break
            
        if candidate:
            candidates.append(candidate)

    if not candidates:
        candidates.extend(_parse_columnar_rows(raw_text, report_date, ocr_confidence))
    candidates = _deduplicate(candidates)

    if not candidates:
        try:
            with open("failed_ocr.txt", "w", encoding="utf-8") as f:
                f.write(raw_text)
        except OSError:
            pass
        raise ExtractionError(
            "We could not find readable lab rows in this report. Try a clearer scan or check the source text."
        )

    for index, candidate in enumerate(candidates, 1):
        candidate["id"] = f"result_{index}"

    return candidates
