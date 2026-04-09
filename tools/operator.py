"""Operator agent CLI — manage escalated WhatsApp conversations with Claude-assisted drafts."""

import anthropic
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


DRAFT_MODEL = "claude-sonnet-4-6"
DRAFT_MAX_TOKENS = 512

DRAFT_SYSTEM_PROMPT = """\
You are an assistant helping a human operator respond to escalated WhatsApp \
conversations from the #BuildingResilience conference (17 April 2026, Libreville, \
Gabon).

Draft a response to send to the user. Rules:
- Write in the same language as the user's messages
- Be professional, warm, and helpful
- Keep it concise and WhatsApp-friendly (plain text, no markdown)
- Address their specific request or concern
- If you don't have enough context to answer, say so and suggest the operator \
add details before sending\
"""


def draft_response(
    client: anthropic.Anthropic,
    history: list[dict],
    reason: str,
    language: str,
) -> str:
    """Use Claude to draft a response for the operator."""
    formatted_history = "\n".join(
        f"{msg['role']}: {msg['content']}" for msg in history
    )

    user_message = (
        f"Escalation reason: {reason}\n\n"
        f"Conversation history:\n{formatted_history}\n\n"
        f"Draft a response to the user's latest message."
    )

    response = client.messages.create(
        model=DRAFT_MODEL,
        max_tokens=DRAFT_MAX_TOKENS,
        system=DRAFT_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    return next(
        (block.text for block in response.content if block.type == "text"), ""
    )
