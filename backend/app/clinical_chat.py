from __future__ import annotations

import re
from typing import Any

from .explanations import explain_result
from .guardrail import guardrail

CHAT_DISCLAIMER = "This assistant explains information found in the uploaded report. It is not a diagnosis or medical advice. Consult a licensed clinician for personal decisions."


def _question_requests_decision(question: str) -> bool:
    return bool(re.search(r"\b(diagnos|disease|cancer|what do i have|should i take|should i stop|medication|treatment|cure|emergency|dangerous)\w*\b", question, re.I))


def _find_results(question: str, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lowered = question.casefold()
    matches = [result for result in results if result.get("raw_test_name", "").casefold() in lowered]
    return matches or results


def answer_question(question: str, report: dict[str, Any]) -> dict[str, Any]:
    question = question.strip()
    if not question:
        return {"answer": "Ask a question about a test, value, unit, reference range, or the report text.", "disclaimer": CHAT_DISCLAIMER}
    if _question_requests_decision(question):
        answer = "I cannot diagnose a condition, recommend treatment, or decide whether something is an emergency. I can describe what is recorded in this report. Please consult a licensed clinician for personal medical advice."
        return {"answer": answer, "disclaimer": CHAT_DISCLAIMER, "refused": True}

    results = _find_results(question, report.get("results", []))
    if not results:
        answer = "I could not find any confirmed test results in this report that answer that question. Please check the source document or ask a licensed clinician."
    elif len(results) == 1:
        answer = explain_result(results[0])
    else:
        lines = [f"The confirmed report contains {len(results)} test results:"]
        lines.extend(f"- {result.get('raw_test_name')}: {result.get('value', 'not available')} {result.get('unit') or ''}".strip() for result in results)
        answer = "\n".join(lines) + "\nI can describe a specific test if you name it. Please consult a licensed clinician for personal interpretation."
    return {"answer": guardrail(answer), "disclaimer": CHAT_DISCLAIMER, "refused": False}
