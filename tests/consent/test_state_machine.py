from unittest.mock import MagicMock
from app.consent.state_machine import resolve_consent_state, process_message


def _mock_supabase(row=None):
    """Create a mock Supabase client that returns the given row."""
    sb = MagicMock()
    query = sb.table.return_value.select.return_value.eq.return_value.execute
    if row:
        query.return_value.data = [row]
    else:
        query.return_value.data = []
    return sb


def test_resolve_unknown_when_no_row():
    sb = _mock_supabase(row=None)
    state = resolve_consent_state(sb, "somehash")
    assert state is None


def test_resolve_registered():
    sb = _mock_supabase(row={"consent_status": "registered", "language": "fr"})
    state = resolve_consent_state(sb, "somehash")
    assert state["consent_status"] == "registered"
    assert state["language"] == "fr"


def test_resolve_active():
    sb = _mock_supabase(row={"consent_status": "active", "language": "en"})
    state = resolve_consent_state(sb, "somehash")
    assert state["consent_status"] == "active"


def test_process_unknown_sender():
    sb = _mock_supabase(row=None)
    result = process_message(sb, "+447700900000", "hello")
    assert result["action"] == "reject"
    assert "réservé" in result["reply"]


def test_process_registered_with_consent_keyword():
    sb = _mock_supabase(row={"consent_status": "registered", "language": "en"})
    sb.table.return_value.update.return_value.eq.return_value.execute.return_value = None
    result = process_message(sb, "+447700900000", "YES")
    assert result["action"] == "activate"
    sb.table.return_value.update.assert_called()


def test_process_registered_without_consent_keyword():
    sb = _mock_supabase(row={"consent_status": "registered", "language": "fr"})
    result = process_message(sb, "+447700900000", "bonjour")
    assert result["action"] == "prompt_consent"
    assert "Répondez OUI" in result["reply"]


def test_process_active_normal_message():
    sb = _mock_supabase(row={"consent_status": "active", "language": "en"})
    result = process_message(sb, "+447700900000", "What is the event schedule?")
    assert result["action"] == "forward_to_ai"


def test_process_active_opt_out():
    sb = _mock_supabase(row={"consent_status": "active", "language": "en"})
    sb.table.return_value.update.return_value.eq.return_value.execute.return_value = None
    result = process_message(sb, "+447700900000", "STOP")
    assert result["action"] == "opt_out"
    assert "unsubscribed" in result["reply"]
    sb.table.return_value.update.assert_called()


def test_process_opted_out_rejoin():
    sb = _mock_supabase(row={"consent_status": "opted_out", "language": "fr"})
    sb.table.return_value.update.return_value.eq.return_value.execute.return_value = None
    result = process_message(sb, "+447700900000", "REJOINDRE")
    assert result["action"] == "rejoin"
    assert "Bon retour" in result["reply"]
    sb.table.return_value.update.assert_called()


def test_process_opted_out_no_rejoin():
    sb = _mock_supabase(row={"consent_status": "opted_out", "language": "en"})
    result = process_message(sb, "+447700900000", "hello")
    assert result["action"] == "remind_opted_out"
    assert "unsubscribed" in result["reply"]
