from unittest.mock import patch, MagicMock

from app.ai.client import get_ai_response, MODEL, ERROR_MESSAGES


def _mock_claude_response(text):
    """Create a mock Anthropic Messages response."""
    response = MagicMock()
    block = MagicMock()
    block.text = text
    response.content = [block]
    return response


@patch("app.ai.client.anthropic.Anthropic")
def test_get_ai_response_returns_text(mock_anthropic_cls):
    mock_client = mock_anthropic_cls.return_value
    mock_client.messages.create.return_value = _mock_claude_response("Bonjour!")
    history = [{"role": "user", "content": "Salut"}]
    result = get_ai_response(history, "fr")
    assert result == "Bonjour!"
    mock_client.messages.create.assert_called_once()


@patch("app.ai.client.anthropic.Anthropic")
def test_get_ai_response_passes_correct_model(mock_anthropic_cls):
    mock_client = mock_anthropic_cls.return_value
    mock_client.messages.create.return_value = _mock_claude_response("Hi!")
    get_ai_response([{"role": "user", "content": "Hi"}], "en")
    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == MODEL


@patch("app.ai.client.anthropic.Anthropic")
def test_get_ai_response_passes_history_as_messages(mock_anthropic_cls):
    mock_client = mock_anthropic_cls.return_value
    mock_client.messages.create.return_value = _mock_claude_response("Reply")
    history = [
        {"role": "user", "content": "First"},
        {"role": "assistant", "content": "Response"},
        {"role": "user", "content": "Second"},
    ]
    get_ai_response(history, "fr")
    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["messages"] == history


@patch("app.ai.client.anthropic.Anthropic")
def test_get_ai_response_returns_error_message_on_failure(mock_anthropic_cls):
    mock_client = mock_anthropic_cls.return_value
    mock_client.messages.create.side_effect = Exception("API error")
    result = get_ai_response([{"role": "user", "content": "Hi"}], "fr")
    assert result == ERROR_MESSAGES["fr"]


@patch("app.ai.client.anthropic.Anthropic")
def test_get_ai_response_error_message_in_english(mock_anthropic_cls):
    mock_client = mock_anthropic_cls.return_value
    mock_client.messages.create.side_effect = Exception("API error")
    result = get_ai_response([{"role": "user", "content": "Hi"}], "en")
    assert result == ERROR_MESSAGES["en"]
