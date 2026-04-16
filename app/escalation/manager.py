from datetime import datetime, timezone

from supabase import Client

from app.escalation.notifier import notify_operators

ESCALATIONS_TABLE = "wa_escalations"


def create_escalation(
    supabase: Client,
    conversation_id: str,
    phone_hash: str,
    reason: str | None,
    user_message: str,
) -> None:
    """Insert a new open escalation and alert operators by email."""
    supabase.table(ESCALATIONS_TABLE).insert({
        "conversation_id": conversation_id,
        "phone_hash": phone_hash,
        "reason": reason,
        "user_message": user_message,
        "status": "open",
    }).execute()
    notify_operators(reason=reason, user_message=user_message, phone_hash=phone_hash)


def get_open_escalation(supabase: Client, phone_hash: str) -> dict | None:
    """Return the open escalation for a phone_hash, or None."""
    result = (
        supabase.table(ESCALATIONS_TABLE)
        .select("*")
        .eq("phone_hash", phone_hash)
        .eq("status", "open")
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def resolve_escalation(supabase: Client, phone_hash: str) -> bool:
    """Resolve the open escalation for a phone_hash. Returns True if one was resolved."""
    now = datetime.now(timezone.utc).isoformat()
    result = (
        supabase.table(ESCALATIONS_TABLE)
        .update({"status": "resolved", "resolved_at": now})
        .eq("phone_hash", phone_hash)
        .eq("status", "open")
        .execute()
    )
    return len(result.data) > 0
