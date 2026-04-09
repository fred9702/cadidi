import re

_ESCALATE_PATTERN = re.compile(
    r"^\[escalate\](?:\[reason:\s*(.+?)\])?(.*)",
    re.IGNORECASE | re.DOTALL,
)


def parse_response(raw: str) -> dict:
    """Parse Claude's response for escalation markers.

    Returns dict with keys: escalated (bool), reason (str|None), reply (str).
    """
    match = _ESCALATE_PATTERN.match(raw.strip())
    if not match:
        return {"escalated": False, "reason": None, "reply": raw}
    reason = match.group(1)
    reply = match.group(2).strip()
    return {"escalated": True, "reason": reason, "reply": reply}
