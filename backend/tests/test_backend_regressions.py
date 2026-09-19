from datetime import datetime

from fastapi.testclient import TestClient

from app.main import app, reports
from app.normalization import normalize_result


client = TestClient(app)


def setup_function() -> None:
    reports.clear()


def add_report(report_id: str, patient_id: str, status: str = "confirmed") -> None:
    reports[report_id] = {
        "id": report_id,
        "filename": f"{report_id}.png",
        "source_type": "image",
        "ocr_confidence": 0.9,
        "patient_id": patient_id,
        "status": status,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "results": [],
    }


def test_delete_data_only_removes_requested_patient() -> None:
    add_report("report_a", "patient_a")
    add_report("report_b", "patient_b")

    response = client.delete("/api/patients/patient_a/data")

    assert response.status_code == 200
    assert "report_a" not in reports
    assert "report_b" in reports


def test_safe_conversion_updates_value_and_reference_range() -> None:
    result = normalize_result(
        {
            "raw_test_name": "Glucose",
            "value": 100.0,
            "unit": "mg/dL",
            "reference_range_low": 70.0,
            "reference_range_high": 100.0,
        }
    )

    assert result["canonical_test_id"] == "glucose"
    assert result["unit"] == "mg/dL"
    assert result["value"] == 100.0
    assert result["reference_range_low"] == 70.0
    assert result["reference_range_high"] == 100.0


def test_safe_conversion_from_mmol_updates_all_numeric_fields() -> None:
    result = normalize_result(
        {
            "raw_test_name": "Glucose",
            "value": 5.55,
            "unit": "mmol/L",
            "reference_range_low": 3.89,
            "reference_range_high": 5.55,
        }
    )

    assert result["unit"] == "mg/dL"
    assert result["value"] == 99.9
    assert result["reference_range_low"] == 70.02
    assert result["reference_range_high"] == 99.9


def test_unsupported_conversion_preserves_value_range_and_unit() -> None:
    result = normalize_result(
        {
            "raw_test_name": "TSH",
            "value": 2.4,
            "unit": "unknown",
            "reference_range_low": 0.4,
            "reference_range_high": 4.0,
        }
    )

    assert result["value"] == 2.4
    assert result["unit"] == "unknown"
    assert result["reference_range_low"] == 0.4
    assert result["reference_range_high"] == 4.0
