from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


def _mock_supabase_with_conversation(conv_data=None):
    """Mock Supabase for conversation lookup and message insert."""
    sb = MagicMock()
    # get_or_create_conversation chain: .select().eq().eq().execute()
    conv_result = MagicMock()
    conv_result.data = [conv_data] if conv_data else []
    sb.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = conv_result
    sb.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = conv_result
    # insert chain
    sb.table.return_value.insert.return_value.execute.return_value = None
    # update chain (for resolve)
    update_result = MagicMock()
    update_result.data = [{"id": "esc-1"}] if conv_data else []
    sb.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = update_result
    return sb


@patch("app.twilio_client.send_whatsapp")
@patch("app.escalation.router.get_supabase")
@patch("app.broadcast.auth.config", return_value="valid-key")
def test_respond_sends_message(mock_config, mock_sb, mock_send):
    conv = {"id": "conv-123", "status": "active", "phone_hash": "abc"}
    mock_sb.return_value = _mock_supabase_with_conversation(conv)
    from main import app
    client = TestClient(app)
    response = client.post(
        "/respond",
        json={"phone": "+241060000001", "message": "We'll handle this for you."},
        headers={"Authorization": "Bearer valid-key"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "sent"
    mock_send.assert_called_once_with("+241060000001", "We'll handle this for you.")


@patch("app.escalation.router.get_supabase")
@patch("app.broadcast.auth.config", return_value="valid-key")
def test_respond_returns_404_no_conversation(mock_config, mock_sb):
    mock_sb.return_value = _mock_supabase_with_conversation(None)
    from main import app
    client = TestClient(app)
    response = client.post(
        "/respond",
        json={"phone": "+241060000001", "message": "Hello"},
        headers={"Authorization": "Bearer valid-key"},
    )
    assert response.status_code == 404


@patch("app.broadcast.auth.config", return_value="valid-key")
def test_respond_rejects_invalid_auth(mock_config):
    from main import app
    client = TestClient(app)
    response = client.post(
        "/respond",
        json={"phone": "+241060000001", "message": "Hello"},
        headers={"Authorization": "Bearer wrong-key"},
    )
    assert response.status_code == 401


@patch("app.broadcast.auth.config", return_value="valid-key")
def test_respond_rejects_missing_fields(mock_config):
    from main import app
    client = TestClient(app)
    response = client.post(
        "/respond",
        json={"phone": "+241060000001"},
        headers={"Authorization": "Bearer valid-key"},
    )
    assert response.status_code == 422


@patch("app.escalation.router.get_supabase")
@patch("app.broadcast.auth.config", return_value="valid-key")
def test_resolve_closes_escalation(mock_config, mock_sb):
    conv = {"id": "esc-1", "status": "open"}
    mock_sb.return_value = _mock_supabase_with_conversation(conv)
    from main import app
    client = TestClient(app)
    response = client.post(
        "/resolve",
        json={"phone": "+241060000001"},
        headers={"Authorization": "Bearer valid-key"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "resolved"


@patch("app.escalation.router.get_supabase")
@patch("app.broadcast.auth.config", return_value="valid-key")
def test_resolve_returns_404_no_open_escalation(mock_config, mock_sb):
    mock_sb.return_value = _mock_supabase_with_conversation(None)
    from main import app
    client = TestClient(app)
    response = client.post(
        "/resolve",
        json={"phone": "+241060000001"},
        headers={"Authorization": "Bearer valid-key"},
    )
    assert response.status_code == 404
