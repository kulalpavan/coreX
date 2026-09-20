from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TestDefinition:
    canonical_test_id: str
    canonical_unit: str | None
    synonyms: tuple[str, ...]
    # Known reference ranges (low, high) — used as fallback when OCR can't read them
    ref_range: tuple[float | None, float | None] | None = None


TEST_DICTIONARY = (
    # ── Complete Blood Count (CBC) ──────────────────────────────────────────
    TestDefinition("hemoglobin", "g/dL",
        ("hemoglobin (hb/hgb)", "hemoglobin (hb)", "haemoglobin (hb)", "hb", "hgb", "haemoglobin", "hemoglobin"),
        (12.0, 17.5)),
    TestDefinition("white_blood_cell_count", "cells/µL",
        ("white blood cell (wbc)", "white blood cell count", "total leukocyte count (tlc)", "total leukocyte count",
         "total wbc count", "white blood cells", "white blood cell", "wbc", "tlc", "leukocytes"),
        (4000.0, 11000.0)),
    TestDefinition("red_blood_cell_count", "cells/µL",
        ("red blood cell (rbc)", "red blood cell count", "rbc count", "red blood cells", "red blood cell", "rbc", "red blood cell count (rbc)"),
        (4.5, 5.9)),
    TestDefinition("hematocrit", "%",
        ("hematocrit (hct)", "packed cell volume (pcv)", "packed cell volume", "hematocrit", "hct", "pcv"),
        (36.0, 52.0)),
    TestDefinition("mcv", "fL",
        ("mean corpuscular volume (mcv)", "mean cell volume (mcv)", "mean cell volume", "mean corpuscular volume", "mcv"),
        (80.0, 100.0)),
    TestDefinition("mch", "pg",
        ("mean corpuscular hemoglobin (mch)", "mean cell hemoglobin (mch)", "mean cell hemoglobin",
         "mean corpuscular hemoglobin", "mch"),
        (27.0, 33.0)),
    TestDefinition("mchc", "g/dL",
        ("mean corpuscular hemoglobin concentration (mchc)", "mean cell hb conc (mchc)",
         "mean corpuscular hemoglobin concentration", "mchc", "mean corpuscular hemoglobin conc (mchc)", "mean corpuscular hemoglobin conc. (mchc)"),
        (32.0, 36.0)),
    TestDefinition("rdw", "%",
        ("red cell distribution width (rdw)", "red cell dist width (rdw)", "red cell distribution width", "rdw"),
        (11.5, 14.5)),
    TestDefinition("platelet_count", "cells/µL",
        ("platelet count", "platelets", "plt"),
        (150000.0, 400000.0)),
    TestDefinition("mpv", "fL",
        ("mean platelet volume (mpv)", "mean platelet volume", "mpv"),
        (7.5, 12.5)),
    # Differential count
    TestDefinition("neutrophil", "%",
        ("neutrophil (neut)", "neutrophil %", "neutrophils %", "neutrophil", "neutrophils", "polymorphs", "neut"),
        (40.0, 75.0)),
    TestDefinition("lymphocyte", "%",
        ("lymphocyte (lymph)", "lymphocyte %", "lymphocytes %", "lymphocyte", "lymphocytes", "lymph"),
        (20.0, 45.0)),
    TestDefinition("monocyte", "%",
        ("monocyte (mono)", "monocyte %", "monocytes %", "monocyte", "monocytes", "mono"),
        (2.0, 10.0)),
    TestDefinition("eosinophil", "%",
        ("eosinophil (eos)", "eosinophil %", "eosinophils %", "eosinophil", "eosinophils", "eos"),
        (1.0, 6.0)),
    TestDefinition("basophil", "%",
        ("basophil (baso)", "basophil %", "basophils %", "basophil", "basophils", "baso"),
        (0.0, 1.0)),
    TestDefinition("neutrophil_abs", "cells/µL",
        ("neutrophil, absolute", "absolute neutrophils", "abs neutrophil"),
        (1800.0, 7500.0)),
    TestDefinition("lymphocyte_abs", "cells/µL",
        ("lymphocyte, absolute", "absolute lymphocytes", "abs lymphocyte"),
        (1000.0, 4800.0)),
    TestDefinition("monocyte_abs", "cells/µL",
        ("monocyte, absolute", "absolute monocytes", "abs monocyte"),
        (100.0, 900.0)),
    TestDefinition("eosinophil_abs", "cells/µL",
        ("eosinophil, absolute", "absolute eosinophils", "abs eosinophil"),
        (100.0, 500.0)),
    TestDefinition("basophil_abs", "cells/µL",
        ("basophil, absolute", "absolute basophils", "abs basophil"),
        (0.0, 100.0)),

    # ── Liver Function Tests (LFT) ──────────────────────────────────────────
    TestDefinition("total_bilirubin", "mg/dL",
        ("total bilirubin (t.bil)", "total bilirubin", "bilirubin total", "t.bil", "tbil"),
        (0.2, 1.2)),
    TestDefinition("direct_bilirubin", "mg/dL",
        ("direct bilirubin (d.bil)", "direct bilirubin", "bilirubin direct", "conjugated bilirubin",
         "direct bilirubin (d. bil)", "d.bil", "dbil"),
        (0.0, 0.4)),
    TestDefinition("indirect_bilirubin", "mg/dL",
        ("indirect bilirubin", "bilirubin indirect", "unconjugated bilirubin"),
        (0.2, 0.8)),
    TestDefinition("ast", "U/L",
        ("aspartate aminotransferase (ast / sgot)", "aspartate aminotransferase (ast/sgot)",
         "aspartate aminotransferase", "ast / sgot", "ast/sgot", "sgot", "ast"),
        (5.0, 40.0)),
    TestDefinition("alt", "U/L",
        ("alanine aminotransferase (alt / sgpt)", "alanine aminotransferase (alt/sgpt)",
         "alanine aminotransferase", "alt / sgpt", "alt/sgpt", "sgpt", "alt"),
        (7.0, 56.0)),
    TestDefinition("alp", "U/L",
        ("alkaline phosphatase (alp)", "alkaline phosphatase", "alp"),
        (44.0, 147.0)),
    TestDefinition("ggt", "U/L",
        ("gamma-glutamyl transferase (ggt)", "gamma glutamyl transferase", "ggt"),
        (9.0, 48.0)),
    TestDefinition("total_protein", "g/dL",
        ("total protein", "serum total protein"),
        (6.4, 8.3)),
    TestDefinition("albumin", "g/dL",
        ("albumin", "serum albumin"),
        (3.5, 5.2)),
    TestDefinition("globulin", "g/dL",
        ("globulin", "serum globulin"),
        (2.0, 3.5)),
    TestDefinition("ag_ratio", None,
        ("a/g ratio", "aig ratio", "albumin/globulin ratio", "a:g ratio"),
        (1.0, 2.0)),

    # ── Kidney Function Tests ────────────────────────────────────────────────
    TestDefinition("creatinine", "mg/dL",
        ("serum creatinine", "creatinine", "s. creatinine"),
        (0.6, 1.2)),
    TestDefinition("urea", "mg/dL",
        ("serum urea", "blood urea", "urea", "bun"),
        (15.0, 45.0)),
    TestDefinition("uric_acid", "mg/dL",
        ("uric acid", "serum uric acid"),
        (2.6, 7.2)),
    TestDefinition("egfr", "mL/min/1.73m²",
        ("egfr (ckd-epi)", "egfr", "estimated gfr", "glomerular filtration rate"),
        (60.0, None)),

    # ── Glucose & Diabetes ───────────────────────────────────────────────────
    TestDefinition("glucose", "mg/dL",
        ("fasting blood glucose (fbs)", "fasting blood glucose", "fasting blood sugar", "fasting glucose",
         "fbs", "blood glucose", "glucose"),
        (70.0, 99.0)),
    TestDefinition("hba1c", "%",
        ("hba1c (glycated hemoglobin)", "glycated hemoglobin (hba1c)", "glycated hemoglobin",
         "hemoglobin a1c", "hba1c", "hb a1c", "a1c"),
        (4.0, 5.6)),
    TestDefinition("postprandial_glucose", "mg/dL",
        ("postprandial blood glucose", "postprandial glucose", "pp blood glucose", "ppbs"),
        (70.0, 140.0)),

    # ── Lipid Profile ────────────────────────────────────────────────────────
    TestDefinition("total_cholesterol", "mg/dL",
        ("total chol", "total cholesterol", "cholesterol", "s. cholesterol"),
        (None, 200.0)),
    TestDefinition("ldl", "mg/dL",
        ("ldl cholesterol", "low density lipoprotein", "ldl-c", "ldl"),
        (None, 100.0)),
    TestDefinition("hdl", "mg/dL",
        ("hdl cholesterol", "high density lipoprotein", "hdl-c", "hdl"),
        (40.0, None)),
    TestDefinition("triglycerides", "mg/dL",
        ("triglycerides", "triglyceride", "tg"),
        (None, 150.0)),
    TestDefinition("vldl", "mg/dL",
        ("vldl cholesterol", "very low density lipoprotein", "vldl-c", "vldl"),
        (5.0, 40.0)),
    TestDefinition("non_hdl", "mg/dL",
        ("non-hdl cholesterol", "non hdl cholesterol"),
        (None, 130.0)),
    TestDefinition("chol_hdl_ratio", None,
        ("total cholesterol / hdl ratio", "chol/hdl ratio", "cholesterol/hdl ratio", "tc/hdl"),
        (None, 5.0)),

    # ── Thyroid ──────────────────────────────────────────────────────────────
    TestDefinition("tsh", "µIU/mL",
        ("thyroid stimulating hormone (tsh)", "thyroid stimulating hormone", "tsh"),
        (0.4, 4.5)),
    TestDefinition("free_t3", "pg/mL",
        ("free t3", "free triiodothyronine", "ft3"),
        (2.3, 4.2)),
    TestDefinition("free_t4", "ng/dL",
        ("free t4", "free thyroxine", "ft4"),
        (0.8, 1.8)),
    TestDefinition("t3", "ng/dL",
        ("total t3", "triiodothyronine", "t3"),
        (80.0, 200.0)),
    TestDefinition("t4", "µg/dL",
        ("total t4", "thyroxine", "t4"),
        (5.0, 12.0)),

    # ── Iron Studies ─────────────────────────────────────────────────────────
    TestDefinition("serum_iron", "µg/dL",
        ("serum iron", "iron", "s. iron"),
        (60.0, 170.0)),
    TestDefinition("tibc", "µg/dL",
        ("total iron binding capacity", "tibc"),
        (250.0, 370.0)),
    TestDefinition("ferritin", "ng/mL",
        ("ferritin", "serum ferritin"),
        (12.0, 300.0)),
    TestDefinition("transferrin_saturation", "%",
        ("transferrin saturation", "iron saturation"),
        (20.0, 50.0)),

    # ── Vitamins ─────────────────────────────────────────────────────────────
    TestDefinition("vitamin_d", "ng/mL",
        ("vitamin d (25-oh)", "25-oh vitamin d", "25-hydroxyvitamin d", "vitamin d", "vit d"),
        (30.0, 100.0)),
    TestDefinition("vitamin_b12", "pg/mL",
        ("vitamin b12", "cobalamin", "vit b12"),
        (200.0, 900.0)),
    TestDefinition("folate", "ng/mL",
        ("folic acid", "serum folate", "folate"),
        (3.0, 17.0)),

    # ── Electrolytes ─────────────────────────────────────────────────────────
    TestDefinition("sodium", "mEq/L",
        ("serum sodium", "sodium", "na+"),
        (136.0, 145.0)),
    TestDefinition("potassium", "mEq/L",
        ("serum potassium", "potassium", "k+"),
        (3.5, 5.0)),
    TestDefinition("chloride", "mEq/L",
        ("serum chloride", "chloride", "cl-"),
        (98.0, 107.0)),
    TestDefinition("bicarbonate", "mEq/L",
        ("bicarbonate", "hco3", "co2"),
        (22.0, 29.0)),
    TestDefinition("calcium", "mg/dL",
        ("serum calcium", "calcium", "ca"),
        (8.5, 10.5)),
    TestDefinition("phosphorus", "mg/dL",
        ("serum phosphorus", "phosphorus", "phosphate"),
        (2.5, 4.5)),
    TestDefinition("magnesium", "mg/dL",
        ("serum magnesium", "magnesium", "mg"),
        (1.7, 2.2)),

    # ── Cardiac Markers ──────────────────────────────────────────────────────
    TestDefinition("troponin_i", "ng/mL",
        ("troponin i", "cardiac troponin i", "ctni"),
        (None, 0.04)),
    TestDefinition("ck_mb", "U/L",
        ("creatine kinase mb", "ck-mb", "ckmb"),
        (None, 25.0)),
    TestDefinition("bnp", "pg/mL",
        ("brain natriuretic peptide", "bnp", "b-type natriuretic peptide"),
        (None, 100.0)),

    # ── Inflammation & Infection ──────────────────────────────────────────────
    TestDefinition("crp", "mg/L",
        ("c-reactive protein", "crp", "hs-crp", "high sensitivity crp"),
        (None, 5.0)),
    TestDefinition("esr", "mm/hr",
        ("erythrocyte sedimentation rate", "esr"),
        (None, 20.0)),
    TestDefinition("procalcitonin", "ng/mL",
        ("procalcitonin", "pct"),
        (None, 0.1)),
)


def _key(value: str) -> str:
    return " ".join(value.casefold().replace("_", " ").split())


def canonical_test_id(raw_test_name: str) -> str | None:
    key = _key(raw_test_name)
    for definition in TEST_DICTIONARY:
        if key in (_key(s) for s in definition.synonyms):
            return definition.canonical_test_id
    return None


def reference_range_for(canonical_id: str) -> tuple[float | None, float | None] | None:
    """Return the known reference range for a canonical test ID, or None if unknown."""
    for definition in TEST_DICTIONARY:
        if definition.canonical_test_id == canonical_id and definition.ref_range is not None:
            return definition.ref_range
    return None


def normalize_result(result: dict) -> dict:
    normalized = dict(result)
    canonical_id = canonical_test_id(result["raw_test_name"])
    if canonical_id:
        normalized["canonical_test_id"] = canonical_id
        
        # 1. Assign canonical unit if missing
        if normalized.get("unit") is None:
            for definition in TEST_DICTIONARY:
                if definition.canonical_test_id == canonical_id:
                    normalized["unit"] = definition.canonical_unit
                    break
                    
        # 2. Perform unit conversion if possible
        conversion = _conversion_for(canonical_id, normalized.get("unit"))
        if conversion is not None:
            factor, canonical_unit = conversion
            normalized["value"] = _convert_number(normalized.get("value"), factor)
            normalized["reference_range_low"] = _convert_number(normalized.get("reference_range_low"), factor)
            normalized["reference_range_high"] = _convert_number(normalized.get("reference_range_high"), factor)
            normalized["unit"] = canonical_unit

        # ── Reference range quality check ──────────────────────────────────────
        # If we have a known reference range, check whether the extracted range is plausible.
        # We override if:
        #   a) No range was extracted (both None), or
        #   b) The extracted range is clearly implausible relative to the value
        known = reference_range_for(canonical_id)
        ext_low = normalized.get("reference_range_low")
        ext_high = normalized.get("reference_range_high")
        value = normalized.get("value")

        def _range_plausible(low, high, val, known_low, known_high) -> bool:
            """Return False if the extracted range is obviously wrong."""
            if low is None and high is None:
                return False  # no range at all → override
            # If both bounds are present, check they bracket the value
            if low is not None and high is not None and val is not None:
                # Range 10x too large vs known range → likely OCR multiply error
                known_span = (known_high or 0) - (known_low or 0)
                ext_span = high - low
                if known_span > 0 and ext_span > known_span * 8:
                    return False
                # Range doesn't bracket the value AT ALL and known range does
                if val < low or val > high:
                    if known_low is not None and known_high is not None:
                        if known_low <= val <= known_high:
                            return False
            return True

        if known is not None:
            known_low, known_high = known
            if not _range_plausible(ext_low, ext_high, value, known_low, known_high):
                normalized["reference_range_low"] = known_low
                normalized["reference_range_high"] = known_high
                normalized["_range_source"] = "knowledge_base"

    return normalized


def _convert_number(value: float | None, factor: float) -> float | None:
    if value is None:
        return None
    return round(value * factor, 3)


def _conversion_for(canonical_id: str, unit: str | None) -> tuple[float, str] | None:
    if unit is None:
        return None
    source = unit.casefold().replace("μ", "u").replace("µ", "u")
    conversions = {
        ("glucose", "mmol/l"): (18.0, "mg/dL"),
        ("total_cholesterol", "mmol/l"): (38.67, "mg/dL"),
        ("ldl", "mmol/l"): (38.67, "mg/dL"),
        ("hdl", "mmol/l"): (38.67, "mg/dL"),
        ("triglycerides", "mmol/l"): (88.57, "mg/dL"),
        ("creatinine", "umol/l"): (1 / 88.4, "mg/dL"),
        # Normalise OCR unit spellings for platelet/RBC WITHOUT scaling the value
        # (doctors read these in the same scale as the report)
    }
    return conversions.get((canonical_id, source))
