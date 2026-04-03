from unittest.mock import MagicMock

from app.ai.history import save_message, load_history, DEFAULT_HISTORY_LIMIT

MESSAGES_TABLE = "wa_messages"


def test_save_message_inserts_row():
    sb = MagicMock()
    sb.table.return_value.insert.return_value.execute.return_value = None
    save_message(sb, "conv-123", "user", "Hello")
    sb.table.return_value.insert.assert_called_once_with({
        "conversation_id": "conv-123",
        "role": "user",
        "content": "Hello",
    })


def test_load_history_returns_formatted_messages():
    sb = MagicMock()
    rows = [
        {"role": "user", "content": "Hi", "created_at": "2026-04-02T10:00:00"},
        {"role": "assistant", "content": "Hello!", "created_at": "2026-04-02T10:00:01"},
    ]
    sb.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = rows
    history = load_history(sb, "conv-123")
    assert history == [
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello!"},
    ]


def test_load_history_empty_conversation():
    sb = MagicMock()
    sb.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []
    history = load_history(sb, "conv-123")
    assert history == []


def test_default_history_limit_is_20():
    assert DEFAULT_HISTORY_LIMIT == 20
