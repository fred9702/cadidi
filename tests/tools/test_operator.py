import sys
import os

# Add project root to path so tools/ is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from unittest.mock import patch, MagicMock
import httpx
from tools.operator import fetch_open_escalations, fetch_conversation_history, draft_response, send_response, resolve_escalation


def _mock_supabase():
    return MagicMock()


def test_fetch_open_escalations_returns_enriched_list():
    sb = _mock_supabase()

    esc_result = MagicMock()
    esc_result.data = [
        {
            "id": "esc-1",
            "conversation_id": "conv-1",
            "phone_hash": "hash-abc",
            "reason": "VIP request",
            "user_message": "I need help",
            "created_at": "2026-04-17T10:00:00Z",
        }
    ]

    reg_result = MagicMock()
    reg_result.data = [{"phone": "+241060000001"}]

    conv_result = MagicMock()
    conv_result.data = [{"language": "fr"}]

    def table_router(name):
        chain = MagicMock()
        if name == "wa_escalations":
            chain.select.return_value.eq.return_value.order.return_value.execute.return_value = esc_result
        elif name == "registrations":
            chain.select.return_value.eq.return_value.execute.return_value = reg_result
        elif name == "wa_conversations":
            chain.select.return_value.eq.return_value.execute.return_value = conv_result
        return chain

    sb.table = table_router

    result = fetch_open_escalations(sb)
    assert len(result) == 1
    assert result[0]["phone"] == "+241060000001"
    assert result[0]["language"] == "fr"
    assert result[0]["reason"] == "VIP request"


def test_fetch_open_escalations_returns_empty_list():
    sb = _mock_supabase()
    esc_result = MagicMock()
    esc_result.data = []

    def table_router(name):
        chain = MagicMock()
        if name == "wa_escalations":
            chain.select.return_value.eq.return_value.order.return_value.execute.return_value = esc_result
        return chain

    sb.table = table_router

    result = fetch_open_escalations(sb)
    assert result == []


def test_fetch_conversation_history():
    sb = _mock_supabase()
    msg_result = MagicMock()
    msg_result.data = [
        {"role": "user", "content": "Hello", "created_at": "2026-04-17T10:00:00Z"},
        {"role": "assistant", "content": "Hi there", "created_at": "2026-04-17T10:00:05Z"},
    ]
    sb.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = msg_result

    result = fetch_conversation_history(sb, "conv-1")
    assert len(result) == 2
    assert result[0]["role"] == "user"
    assert result[1]["role"] == "assistant"


def test_draft_response_calls_claude():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(type="text", text="Bonjour, je vais vous aider.")]
    mock_client.messages.create.return_value = mock_response

    history = [
        {"role": "user", "content": "J'ai besoin d'aide", "created_at": "2026-04-17T10:00:00Z"},
    ]

    result = draft_response(mock_client, history, "VIP logistics", "fr")
    assert result == "Bonjour, je vais vous aider."

    call_kwargs = mock_client.messages.create.call_args[1]
    assert call_kwargs["model"] == "claude-sonnet-4-6"
    assert call_kwargs["max_tokens"] == 512
    assert "VIP logistics" in call_kwargs["messages"][0]["content"]


def test_draft_response_includes_history():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(type="text", text="Response")]
    mock_client.messages.create.return_value = mock_response

    history = [
        {"role": "user", "content": "Hello", "created_at": "2026-04-17T10:00:00Z"},
        {"role": "assistant", "content": "Hi", "created_at": "2026-04-17T10:00:05Z"},
        {"role": "user", "content": "Help me", "created_at": "2026-04-17T10:00:10Z"},
    ]

    draft_response(mock_client, history, "General help", "en")

    call_kwargs = mock_client.messages.create.call_args[1]
    user_msg = call_kwargs["messages"][0]["content"]
    assert "Hello" in user_msg
    assert "Hi" in user_msg
    assert "Help me" in user_msg


def test_send_response_success():
    with patch("tools.operator.httpx.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status": "sent"}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        success, detail = send_response(
            "http://localhost:8000", "test-key", "+241060000001", "Hello"
        )
        assert success is True
        assert detail == {"status": "sent"}

        mock_post.assert_called_once_with(
            "http://localhost:8000/respond",
            json={"phone": "+241060000001", "message": "Hello"},
            headers={"Authorization": "Bearer test-key"},
            timeout=30,
        )


def test_send_response_failure():
    with patch("tools.operator.httpx.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.json.return_value = {"detail": "No active conversation"}
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404", request=MagicMock(), response=mock_resp
        )
        mock_post.return_value = mock_resp

        success, detail = send_response(
            "http://localhost:8000", "test-key", "+241060000001", "Hello"
        )
        assert success is False


def test_resolve_escalation_success():
    with patch("tools.operator.httpx.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status": "resolved"}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        success, detail = resolve_escalation(
            "http://localhost:8000", "test-key", "+241060000001"
        )
        assert success is True
        assert detail == {"status": "resolved"}


def test_resolve_escalation_failure():
    with patch("tools.operator.httpx.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.json.return_value = {"detail": "No open escalation"}
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404", request=MagicMock(), response=mock_resp
        )
        mock_post.return_value = mock_resp

        success, detail = resolve_escalation(
            "http://localhost:8000", "test-key", "+241060000001"
        )
        assert success is False
