from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TestDefinition:
    canonical_test_id: str
    canonical_unit: str | None
    synonyms: tuple[str, ...]


TEST_DICTIONARY = (
    TestDefinition("hemoglobin", "g/dL", ("hb", "hgb", "haemoglobin", "hemoglobin")),
    TestDefinition("total_cholesterol", "mg/dL", ("total chol", "total cholesterol", "cholesterol")),
    TestDefinition("ldl", "mg/dL", ("ldl", "ldl cholesterol")),
    TestDefinition("hdl", "mg/dL", ("hdl", "hdl cholesterol")),
    TestDefinition("triglycerides", "mg/dL", ("tg", "triglycerides", "triglyceride")),
    TestDefinition("tsh", "mIU/L", ("tsh", "thyroid stimulating hormone")),
    TestDefinition("alt", "U/L", ("alt", "sgpt")),
    TestDefinition("ast", "U/L", ("ast", "sgot")),
    TestDefinition("creatinine", "mg/dL", ("creatinine", "serum creatinine")),
    TestDefinition("glucose", "mg/dL", ("glucose", "blood glucose", "fasting glucose")),
)


def _key(value: str) -> str:
    return " ".join(value.casefold().replace("_", " ").split())


def canonical_test_id(raw_test_name: str) -> str | None:
    key = _key(raw_test_name)
    for definition in TEST_DICTIONARY:
        if key in definition.synonyms:
            return definition.canonical_test_id
    return None


def normalize_result(result: dict) -> dict:
    normalized = dict(result)
    canonical_id = canonical_test_id(result["raw_test_name"])
    if canonical_id:
        normalized["canonical_test_id"] = canonical_id
        normalized["value"], normalized["unit"] = _convert_value(
            canonical_id, result.get("value"), result.get("unit")
        )
    return normalized


def _convert_value(canonical_id: str, value: float | None, unit: str | None) -> tuple[float | None, str | None]:
    if value is None or unit is None:
        return value, unit
    source = unit.casefold().replace("μ", "u").replace("µ", "u")
    conversions = {
        ("glucose", "mmol/l"): (18.0, "mg/dL"),
        ("total_cholesterol", "mmol/l"): (38.67, "mg/dL"),
        ("ldl", "mmol/l"): (38.67, "mg/dL"),
        ("hdl", "mmol/l"): (38.67, "mg/dL"),
        ("triglycerides", "mmol/l"): (88.57, "mg/dL"),
        ("creatinine", "umol/l"): (1 / 88.4, "mg/dL"),
    }
    conversion = conversions.get((canonical_id, source))
    if conversion is None:
        return value, unit
    factor, canonical_unit = conversion
    return round(value * factor, 3), canonical_unit
