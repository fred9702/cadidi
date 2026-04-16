import re

# Escalation must start at the beginning of the response (after optional
# leading whitespace) to avoid false positives when the assistant
# legitimately quotes the tag inside a longer reply. The [REASON: ...]
# block is optional, and any whitespace/newlines between the tags and
# the user-facing reply are tolerated.
_ESCALATE_PATTERN = re.compile(
    r"^\s*\[escalate\]\s*(?:\[reason:\s*(.*?)\])?\s*(.*)",
    re.IGNORECASE | re.DOTALL,
)


def parse_response(raw: str) -> dict:
    """Parse Claude's response for escalation markers.

    Returns dict with keys: escalated (bool), reason (str|None), reply (str).
    """
    match = _ESCALATE_PATTERN.match(raw)
    if not match:
        return {"escalated": False, "reason": None, "reply": raw}
    reason = match.group(1)
    reply = match.group(2).strip()
    if reason is not None:
        reason = reason.strip() or None
    return {"escalated": True, "reason": reason, "reply": reply}
