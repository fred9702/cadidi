from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient


def _mock_supabase_with_state(state_row):
    """Return a mock Supabase client that returns state_row on lookup."""
    sb = MagicMock()
    query = sb.table.return_value.select.return_value.eq.return_value.execute
    if state_row:
        query.return_value.data = [state_row]
    else:
        query.return_value.data = []
    sb.table.return_value.update.return_value.eq.return_value.execute.return_value = None
    return sb


@patch("main.send_whatsapp")
@patch("main.get_supabase")
def test_unknown_sender_gets_rejection(mock_get_sb, mock_send):
    mock_get_sb.return_value = _mock_supabase_with_state(None)
    from main import app
    client = TestClient(app)
    response = client.post("/message", data={"From": "whatsapp:+440000000000", "Body": "hello"})
    assert response.status_code == 200
    mock_send.assert_called_once()
    assert "réservé" in mock_send.call_args[0][1]


@patch("main.send_whatsapp")
@patch("main.get_supabase")
def test_registered_sender_gets_consent_prompt(mock_get_sb, mock_send):
    mock_get_sb.return_value = _mock_supabase_with_state(
        {"consent_status": "registered", "language_pref": "en"}
    )
    from main import app
    client = TestClient(app)
    response = client.post("/message", data={"From": "whatsapp:+441111111111", "Body": "hi"})
    assert response.status_code == 200
    mock_send.assert_called_once()
    assert "Reply YES" in mock_send.call_args[0][1]


@patch("main.send_whatsapp")
@patch("main.get_supabase")
@patch("main.run_ai_query")
def test_active_sender_gets_ai_response(mock_ai, mock_get_sb, mock_send):
    mock_get_sb.return_value = _mock_supabase_with_state(
        {"consent_status": "active", "language_pref": "en"}
    )
    mock_ai.return_value = "The event starts at 9am."
    from main import app
    client = TestClient(app)
    response = client.post("/message", data={"From": "whatsapp:+442222222222", "Body": "When does it start?"})
    assert response.status_code == 200
    mock_send.assert_called_once()
    assert "9am" in mock_send.call_args[0][1]


@patch("main.send_whatsapp")
@patch("main.get_supabase")
def test_active_sender_opts_out(mock_get_sb, mock_send):
    mock_get_sb.return_value = _mock_supabase_with_state(
        {"consent_status": "active", "language_pref": "fr"}
    )
    from main import app
    client = TestClient(app)
    response = client.post("/message", data={"From": "whatsapp:+443333333333", "Body": "STOP"})
    assert response.status_code == 200
    mock_send.assert_called_once()
    assert "désabonné" in mock_send.call_args[0][1]
