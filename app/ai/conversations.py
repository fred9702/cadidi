from datetime import datetime, timezone, timedelta

from supabase import Client

SESSION_EXPIRY_HOURS = 24
CONVERSATIONS_TABLE = "wa_conversations"


def get_or_create_conversation(supabase: Client, phone_hash: str, language: str) -> dict:
    """Get an active conversation or create a new one.

    Expires conversations older than SESSION_EXPIRY_HOURS.
    """
    result = (
        supabase.table(CONVERSATIONS_TABLE)
        .select("*")
        .eq("phone_hash", phone_hash)
        .eq("status", "active")
        .execute()
    )

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=SESSION_EXPIRY_HOURS)

    if result.data:
        conv = result.data[0]
        last_msg = datetime.fromisoformat(conv["last_message_at"])
        if last_msg > cutoff:
            # Active and fresh — update timestamp
            supabase.table(CONVERSATIONS_TABLE).update(
                {"last_message_at": now.isoformat()}
            ).eq("id", conv["id"]).execute()
            return conv
        # Stale — expire it
        supabase.table(CONVERSATIONS_TABLE).update(
            {"status": "expired"}
        ).eq("id", conv["id"]).execute()

    # Create new conversation
    new_conv = (
        supabase.table(CONVERSATIONS_TABLE)
        .insert({
            "phone_hash": phone_hash,
            "language": language,
            "status": "active",
            "started_at": now.isoformat(),
            "last_message_at": now.isoformat(),
        })
        .execute()
    )
    return new_conv.data[0]
