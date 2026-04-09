"""Operator agent CLI — manage escalated WhatsApp conversations with Claude-assisted drafts."""

from supabase import Client


def fetch_open_escalations(supabase: Client) -> list[dict]:
    """Fetch open escalations enriched with phone number and language."""
    esc_result = (
        supabase.table("wa_escalations")
        .select("id, conversation_id, phone_hash, reason, user_message, created_at")
        .eq("status", "open")
        .order("created_at")
        .execute()
    )

    if not esc_result.data:
        return []

    enriched = []
    for esc in esc_result.data:
        reg = (
            supabase.table("registrations")
            .select("phone")
            .eq("phone_hash", esc["phone_hash"])
            .execute()
        )
        phone = reg.data[0]["phone"] if reg.data else None

        conv = (
            supabase.table("wa_conversations")
            .select("language")
            .eq("id", esc["conversation_id"])
            .execute()
        )
        language = conv.data[0]["language"] if conv.data else "fr"

        enriched.append({
            **esc,
            "phone": phone,
            "language": language,
        })

    return enriched


def fetch_conversation_history(supabase: Client, conversation_id: str) -> list[dict]:
    """Fetch message history for a conversation, ordered by time."""
    result = (
        supabase.table("wa_messages")
        .select("role, content, created_at")
        .eq("conversation_id", conversation_id)
        .order("created_at")
        .execute()
    )
    return result.data
