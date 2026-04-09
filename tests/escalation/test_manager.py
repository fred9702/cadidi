from unittest.mock import MagicMock
from app.escalation.manager import create_escalation, get_open_escalation, resolve_escalation


def _mock_supabase():
    sb = MagicMock()
    return sb


def test_create_escalation_inserts_row():
    sb = _mock_supabase()
    sb.table.return_value.insert.return_value.execute.return_value = None

    create_escalation(
        sb,
        conversation_id="conv-123",
        phone_hash="hash-abc",
        reason="VIP request",
        user_message="I need help with my seat",
    )

    sb.table.assert_called_with("wa_escalations")
    insert_data = sb.table.return_value.insert.call_args[0][0]
    assert insert_data["conversation_id"] == "conv-123"
    assert insert_data["phone_hash"] == "hash-abc"
    assert insert_data["reason"] == "VIP request"
    assert insert_data["user_message"] == "I need help with my seat"
    assert insert_data["status"] == "open"


def test_get_open_escalation_returns_row():
    sb = _mock_supabase()
    row = {"id": "esc-1", "phone_hash": "hash-abc", "status": "open"}
    sb.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [row]

    result = get_open_escalation(sb, "hash-abc")
    assert result == row


def test_get_open_escalation_returns_none_when_empty():
    sb = _mock_supabase()
    sb.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []

    result = get_open_escalation(sb, "hash-abc")
    assert result is None


def test_resolve_escalation_updates_status():
    sb = _mock_supabase()
    sb.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = [{"id": "esc-1"}]

    result = resolve_escalation(sb, "hash-abc")
    assert result is True

    update_args = sb.table.return_value.update.call_args[0][0]
    assert update_args["status"] == "resolved"
    assert "resolved_at" in update_args


def test_resolve_escalation_returns_false_when_none_open():
    sb = _mock_supabase()
    sb.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = []

    result = resolve_escalation(sb, "hash-abc")
    assert result is False
