import re

CONSENT_WORDS = {"yes", "oui", "si", "sí", "sim"}
OPT_OUT_WORDS = {"stop", "arrêter", "arreter", "parar"}
REJOIN_WORDS = {"join", "rejoindre", "unirse", "juntar"}

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def match_trigger(text: str) -> dict:
    """Match a message against trigger words.

    Returns dict with:
        trigger: 'consent', 'opt_out', 'rejoin', or None
        email: extracted email if consent word + email pattern, else None
    """
    stripped = text.strip()
    normalized = stripped.lower()

    # Exact match — bare trigger word
    if normalized in CONSENT_WORDS:
        return {"trigger": "consent", "email": None}
    if normalized in OPT_OUT_WORDS:
        return {"trigger": "opt_out", "email": None}
    if normalized in REJOIN_WORDS:
        return {"trigger": "rejoin", "email": None}

    # Consent word + email pattern (only for consent, not opt-out/rejoin)
    parts = stripped.split()
    if len(parts) == 2:
        word, candidate_email = parts
        if word.lower() in CONSENT_WORDS and EMAIL_RE.match(candidate_email):
            return {"trigger": "consent", "email": candidate_email}

    return {"trigger": None, "email": None}
