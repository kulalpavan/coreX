from typing import Any


TEST_DESCRIPTIONS = {
    "hemoglobin": "Hemoglobin is a protein in red blood cells that helps carry oxygen.",
    "total_cholesterol": "Total cholesterol is a measure of cholesterol carried in the blood.",
    "tsh": "TSH is a measurement related to thyroid signaling.",
    "free_t4": "Free T4 is a measurement of an available thyroid hormone.",
    "glucose": "Glucose is a type of sugar used by the body for energy.",
}


def explain_result(result: dict[str, Any]) -> str:
    name = result.get("raw_test_name", "This test")
    value = result.get("value")
    unit = result.get("unit") or ""
    low = result.get("reference_range_low")
    high = result.get("reference_range_high")
    canonical_id = result.get("canonical_test_id")
    description = TEST_DESCRIPTIONS.get(canonical_id, f"{name} is a laboratory measurement recorded on this report.")
    value_text = f"{value:g} {unit}".strip() if isinstance(value, (int, float)) else "not available"
    if value is None:
        return f"{name} is recorded as not available. The report does not provide a value to compare. Discuss this result with your clinician for personal context."
    if low is None and high is None:
        return f"{name} is recorded as {value_text}. The report does not include enough reference range information for a comparison. {description} Discuss this result with your clinician for personal context."
    if low is not None and high is not None:
        status = "within" if low <= value <= high else "above" if value > high else "below"
        range_text = f"{low:g}-{high:g} {unit}".strip()
    elif high is not None:
        status = "below or equal to" if value <= high else "above"
        range_text = f"{high:g} {unit}".strip()
    else:
        status = "above or equal to" if value >= low else "below"
        range_text = f"{low:g} {unit}".strip()
    return f"{name} is recorded as {value_text}. This is {status} the reference range provided on the report ({range_text}). {description} Discuss this result with your clinician for personal context."
