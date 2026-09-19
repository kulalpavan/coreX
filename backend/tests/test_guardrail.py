import pytest

from app.guardrail import SAFE_FALLBACK, check_explanation, guardrail


@pytest.mark.parametrize(
    "text",
    [
        "This may diagnose cancer.",
        "You should take your medication now.",
        "This is dangerous and needs emergency treatment.",
        "This result will cure the condition.",
    ],
)
def test_adversarial_explanation_is_replaced(text: str) -> None:
    allowed, reason = check_explanation(text)

    assert allowed is False
    assert reason
    assert guardrail(text) == SAFE_FALLBACK


def test_neutral_explanation_passes_unchanged() -> None:
    text = "This value is within the range printed on the report. Discuss it with your clinician."

    assert check_explanation(text) == (True, None)
    assert guardrail(text) == text
