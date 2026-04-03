from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta

from app.ai.conversations import get_or_create_conversation, SESSION_EXPIRY_HOURS

CONVERSATIONS_TABLE = "wa_conversations"


def _mock_supabase(select_rows=None, insert_row=None):
    """Mock Supabase client for conversation queries."""
    sb = MagicMock()
    table_mock = sb.table.return_value

    # SELECT chain: .select().eq().eq().execute()
    select_chain = table_mock.select.return_value.eq.return_value.eq.return_value
    select_chain.execute.return_value.data = select_rows or []

    # INSERT chain: .insert().execute()
    if insert_row:
        table_mock.insert.return_value.execute.return_value.data = [insert_row]
    else:
        table_mock.insert.return_value.execute.return_value.data = [
            {"id": "new-conv-id", "phone_hash": "abc", "language": "fr",
             "status": "active", "last_message_at": datetime.now(timezone.utc).isoformat()}
        ]

    # UPDATE chain: .update().eq().execute()
    table_mock.update.return_value.eq.return_value.execute.return_value = None

    return sb


def test_creates_new_conversation_when_none_exists():
    sb = _mock_supabase(select_rows=[])
    conv = get_or_create_conversation(sb, "hash123", "fr")
    assert conv["id"] == "new-conv-id"
    sb.table.return_value.insert.assert_called_once()


def test_returns_existing_active_conversation():
    now = datetime.now(timezone.utc)
    existing = {
        "id": "existing-id",
        "phone_hash": "hash123",
        "language": "fr",
        "status": "active",
        "last_message_at": now.isoformat(),
    }
    sb = _mock_supabase(select_rows=[existing])
    conv = get_or_create_conversation(sb, "hash123", "fr")
    assert conv["id"] == "existing-id"
    # Should update last_message_at
    sb.table.return_value.update.assert_called()


def test_expires_stale_conversation_and_creates_new():
    stale_time = (datetime.now(timezone.utc) - timedelta(hours=SESSION_EXPIRY_HOURS + 1)).isoformat()
    stale = {
        "id": "stale-id",
        "phone_hash": "hash123",
        "language": "fr",
        "status": "active",
        "last_message_at": stale_time,
    }
    sb = _mock_supabase(select_rows=[stale])
    conv = get_or_create_conversation(sb, "hash123", "fr")
    # Should have called update twice: once to expire, once for new conversation's last_message_at
    # And insert once for the new conversation
    sb.table.return_value.insert.assert_called_once()


def test_session_expiry_hours_is_24():
    assert SESSION_EXPIRY_HOURS == 24
