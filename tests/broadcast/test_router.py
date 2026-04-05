from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


def _mock_supabase_with_recipients(rows):
    """Mock Supabase returning recipient rows from registrations."""
    sb = MagicMock()
    # Chain: .select().eq().neq().execute() or .select().eq().neq().eq().execute()
    chain = sb.table.return_value.select.return_value
    chain.eq.return_value.neq.return_value.execute.return_value.data = rows
    chain.eq.return_value.neq.return_value.eq.return_value.execute.return_value.data = rows
    return sb


@patch("app.twilio_client.send_whatsapp")
@patch("app.broadcast.router.get_supabase")
@patch("app.broadcast.auth.config", return_value="valid-key")
def test_broadcast_sends_to_active_users(mock_config, mock_sb, mock_send):
    mock_sb.return_value = _mock_supabase_with_recipients([
        {"phone": "+447700900001"},
        {"phone": "+447700900002"},
    ])
    from main import app
    client = TestClient(app)
    response = client.post(
        "/broadcast",
        json={"message": "Hello everyone!"},
        headers={"Authorization": "Bearer valid-key"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["sent"] == 2
    assert data["failed"] == 0


@patch("app.twilio_client.send_whatsapp")
@patch("app.broadcast.router.get_supabase")
@patch("app.broadcast.auth.config", return_value="valid-key")
def test_broadcast_with_language_filter(mock_config, mock_sb, mock_send):
    mock_sb.return_value = _mock_supabase_with_recipients([
        {"phone": "+447700900001"},
    ])
    from main import app
    client = TestClient(app)
    response = client.post(
        "/broadcast",
        json={"message": "Bonjour!", "language": "fr"},
        headers={"Authorization": "Bearer valid-key"},
    )
    assert response.status_code == 200
    assert response.json()["sent"] == 1


@patch("app.broadcast.auth.config", return_value="valid-key")
def test_broadcast_rejects_invalid_key(mock_config):
    from main import app
    client = TestClient(app)
    response = client.post(
        "/broadcast",
        json={"message": "Hello"},
        headers={"Authorization": "Bearer wrong-key"},
    )
    assert response.status_code == 401


@patch("app.broadcast.auth.config", return_value="valid-key")
def test_broadcast_rejects_missing_auth(mock_config):
    from main import app
    client = TestClient(app)
    response = client.post("/broadcast", json={"message": "Hello"})
    assert response.status_code == 401


@patch("app.broadcast.auth.config", return_value="valid-key")
def test_broadcast_rejects_missing_message(mock_config):
    from main import app
    client = TestClient(app)
    response = client.post(
        "/broadcast",
        json={},
        headers={"Authorization": "Bearer valid-key"},
    )
    assert response.status_code == 400


@patch("app.twilio_client.send_whatsapp")
@patch("app.broadcast.router.get_supabase")
@patch("app.broadcast.auth.config", return_value="valid-key")
def test_broadcast_counts_failures(mock_config, mock_sb, mock_send):
    mock_sb.return_value = _mock_supabase_with_recipients([
        {"phone": "+447700900001"},
        {"phone": "+447700900002"},
    ])
    mock_send.side_effect = [None, Exception("Twilio error")]
    from main import app
    client = TestClient(app)
    response = client.post(
        "/broadcast",
        json={"message": "Hello"},
        headers={"Authorization": "Bearer valid-key"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["sent"] == 1
    assert data["failed"] == 1


@patch("app.twilio_client.send_whatsapp")
@patch("app.broadcast.router.get_supabase")
@patch("app.broadcast.auth.config", return_value="valid-key")
def test_broadcast_zero_recipients(mock_config, mock_sb, mock_send):
    mock_sb.return_value = _mock_supabase_with_recipients([])
    from main import app
    client = TestClient(app)
    response = client.post(
        "/broadcast",
        json={"message": "Hello"},
        headers={"Authorization": "Bearer valid-key"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["sent"] == 0
    assert data["failed"] == 0
