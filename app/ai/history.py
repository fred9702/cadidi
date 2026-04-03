from supabase import Client

DEFAULT_HISTORY_LIMIT = 20
MESSAGES_TABLE = "wa_messages"


def save_message(supabase: Client, conversation_id: str, role: str, content: str) -> None:
    """Insert a message into wa_messages."""
    supabase.table(MESSAGES_TABLE).insert({
        "conversation_id": conversation_id,
        "role": role,
        "content": content,
    }).execute()


def load_history(supabase: Client, conversation_id: str, limit: int = DEFAULT_HISTORY_LIMIT) -> list[dict]:
    """Load recent messages for a conversation, formatted for Claude Messages API."""
    result = (
        supabase.table(MESSAGES_TABLE)
        .select("role, content")
        .eq("conversation_id", conversation_id)
        .order("created_at", desc=False)
        .limit(limit)
        .execute()
    )
    return [{"role": row["role"], "content": row["content"]} for row in result.data]
