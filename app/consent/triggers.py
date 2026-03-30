CONSENT_WORDS = {"yes", "oui", "si", "sí", "sim"}
OPT_OUT_WORDS = {"stop", "arrêter", "arreter", "parar"}
REJOIN_WORDS = {"join", "rejoindre", "unirse", "juntar"}


def match_trigger(text: str) -> str | None:
    """Match a message against trigger words. Returns 'consent', 'opt_out', 'rejoin', or None."""
    normalized = text.strip().lower()
    if normalized in CONSENT_WORDS:
        return "consent"
    if normalized in OPT_OUT_WORDS:
        return "opt_out"
    if normalized in REJOIN_WORDS:
        return "rejoin"
    return None
