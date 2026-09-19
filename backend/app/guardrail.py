import re


SAFE_FALLBACK = "This result is available for review. Discuss it with your clinician for personal context."

BLOCKED_PATTERNS = (
    re.compile(r"\b(diagnos|disease|cancer|tumou?r|condition)\w*\b", re.I),
    re.compile(r"\b(take|stop|start|change|increase|decrease)\s+(?:your\s+)?(?:medication|medicine|dose|treatment)\b", re.I),
    re.compile(r"\b(emergency|dangerous|urgent|immediately|life[- ]threatening)\b", re.I),
    re.compile(r"\b(cure|treat|prevent)\b", re.I),
)


def check_explanation(text: str) -> tuple[bool, str | None]:
    for pattern in BLOCKED_PATTERNS:
        match = pattern.search(text)
        if match:
            return False, f"blocked language: {match.group(0)}"
    return True, None


def guardrail(text: str) -> str:
    allowed, _reason = check_explanation(text)
    return text if allowed else SAFE_FALLBACK
