from datetime import datetime, timezone

from supabase import Client

from app.consent.hashing import hash_phone_number, hash_email
from app.consent.triggers import match_trigger
from app.consent.messages import get_message

REGISTRATION_TABLE = "registrations"


def resolve_consent_state(supabase: Client, phone_hash: str) -> dict | None:
    """Look up a phone hash in the registration table. Returns row dict or None."""
    result = (
        supabase.table(REGISTRATION_TABLE)
        .select("consent_status, language_pref")
        .eq("phone_hash", phone_hash)
        .execute()
    )
    if result.data:
        return result.data[0]
    return None


def resolve_consent_state_by_email(supabase: Client, email_hash: str) -> dict | None:
    """Look up an email hash in the registration table. Returns row dict or None."""
    result = (
        supabase.table(REGISTRATION_TABLE)
        .select("consent_status, language_pref, phone_hash")
        .eq("email_hash", email_hash)
        .execute()
    )
    if result.data:
        return result.data[0]
    return None


def _update_consent(supabase: Client, key_value: str, updates: dict, key_column: str = "phone_hash") -> None:
    """Update consent fields on the registration table."""
    supabase.table(REGISTRATION_TABLE).update(updates).eq(
        key_column, key_value
    ).execute()


def process_message(supabase: Client, phone: str, body: str) -> dict:
    """
    Process an incoming WhatsApp message through the consent state machine.

    Returns a dict with:
        action: str — what happened (reject, prompt_consent, activate, forward_to_ai, opt_out, rejoin, remind_opted_out)
        reply: str | None — message to send back (None if forward_to_ai)
    """
    phone_hash = hash_phone_number(phone)
    state = resolve_consent_state(supabase, phone_hash)
    trigger_result = match_trigger(body)
    trigger = trigger_result["trigger"]
    email = trigger_result["email"]

    # Unknown sender — try email fallback
    if state is None:
        if email:
            email_h = hash_email(email)
            state = resolve_consent_state_by_email(supabase, email_h)
            if state is not None:
                # Link this WhatsApp number to the registration for future lookups
                _update_consent(supabase, email_h, {"phone_hash": phone_hash}, key_column="email_hash")
        if state is None:
            return {"action": "reject", "reply": get_message("unknown", "fr")}

    status = state["consent_status"]
    lang = state.get("language_pref", "fr")

    # Registered — awaiting consent
    if status == "registered":
        if trigger == "consent":
            now = datetime.now(timezone.utc).isoformat()
            _update_consent(supabase, phone_hash, {
                "consent_status": "active",
                "consent_given_at": now,
            })
            return {"action": "activate", "reply": None}
        return {"action": "prompt_consent", "reply": get_message("consent_prompt", lang)}

    # Active
    if status == "active":
        if trigger == "opt_out":
            now = datetime.now(timezone.utc).isoformat()
            _update_consent(supabase, phone_hash, {
                "consent_status": "opted_out",
                "consent_revoked_at": now,
            })
            return {"action": "opt_out", "reply": get_message("opted_out", lang)}
        return {"action": "forward_to_ai", "reply": None}

    # Opted out
    if status == "opted_out":
        if trigger == "rejoin":
            now = datetime.now(timezone.utc).isoformat()
            _update_consent(supabase, phone_hash, {
                "consent_status": "active",
                "consent_given_at": now,
                "consent_revoked_at": None,
            })
            return {"action": "rejoin", "reply": get_message("welcome_back", lang)}
        return {"action": "remind_opted_out", "reply": get_message("opted_out", lang)}

    return {"action": "reject", "reply": get_message("unknown", "fr")}
