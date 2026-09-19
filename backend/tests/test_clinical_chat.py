from app.clinical_chat import answer_question


def report():
    return {
        "results": [{
            "raw_test_name": "Hemoglobin",
            "canonical_test_id": "hemoglobin",
            "value": 10.8,
            "unit": "g/dL",
            "reference_range_low": 12.0,
            "reference_range_high": 15.5,
        }]
    }


def test_chat_describes_confirmed_report_value() -> None:
    result = answer_question("What does my Hemoglobin result say?", report())

    assert "10.8" in result["answer"]
    assert "below" in result["answer"]
    assert result["refused"] is False
    assert "not a diagnosis" in result["disclaimer"]


def test_chat_refuses_diagnosis_and_treatment_decisions() -> None:
    result = answer_question("What disease do I have and what medication should I take?", report())

    assert result["refused"] is True
    assert "cannot diagnose" in result["answer"]
    assert "clinician" in result["answer"]


def test_chat_does_not_answer_from_unconfirmed_or_missing_data() -> None:
    result = answer_question("What is my glucose?", {"results": []})

    assert "could not find" in result["answer"]
