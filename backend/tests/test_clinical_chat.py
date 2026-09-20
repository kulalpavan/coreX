from unittest.mock import patch, MagicMock
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

def mock_gemini_response(text):
    mock = MagicMock()
    mock.read.return_value = f'{{"candidates": [{{"content": {{"parts": [{{"text": "{text}"}}]}}}}]}}'.encode("utf-8")
    return mock

@patch("os.getenv", return_value="fake_key")
@patch("urllib.request.urlopen")
def test_chat_describes_confirmed_report_value(mock_urlopen, mock_getenv) -> None:
    mock_urlopen.return_value = mock_gemini_response("Your Hemoglobin is 10.8 g/dL, which is below the normal range.")
    result = answer_question("What does my Hemoglobin result say?", [], report())

    assert "10.8" in result["answer"]
    assert "below" in result["answer"]
    assert result["refused"] is False
    assert "not a diagnosis" in result["disclaimer"]


@patch("os.getenv", return_value="fake_key")
@patch("urllib.request.urlopen")
def test_chat_refuses_diagnosis_and_treatment_decisions(mock_urlopen, mock_getenv) -> None:
    mock_urlopen.return_value = mock_gemini_response("I cannot diagnose conditions or recommend treatment. Please consult your clinician.")
    result = answer_question("What disease do I have and what medication should I take?", [], report())

    assert result["refused"] is True
    assert "cannot diagnose" in result["answer"]
    assert "clinician" in result["answer"]


@patch("os.getenv", return_value="fake_key")
@patch("urllib.request.urlopen")
def test_chat_does_not_answer_from_unconfirmed_or_missing_data(mock_urlopen, mock_getenv) -> None:
    mock_urlopen.return_value = mock_gemini_response("I could not find glucose in your report.")
    result = answer_question("What is my glucose?", [], {"results": []})

    assert "could not find" in result["answer"]
