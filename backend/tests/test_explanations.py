from app.explanations import explain_result


def test_explanation_is_deterministic_and_neutral() -> None:
    text = explain_result({
        "raw_test_name": "Hemoglobin",
        "canonical_test_id": "hemoglobin",
        "value": 10.8,
        "unit": "g/dL",
        "reference_range_low": 12.0,
        "reference_range_high": 15.5,
    })

    assert "below the reference range" in text
    assert "protein in red blood cells" in text
    assert "diagnos" not in text.lower()
    assert "danger" not in text.lower()


def test_missing_reference_range_is_not_invented() -> None:
    text = explain_result({"raw_test_name": "TSH", "value": 2.4, "unit": "mIU/L"})

    assert "does not include enough reference range" in text
    assert "0.4" not in text
