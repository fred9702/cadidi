from unittest.mock import patch, MagicMock

from app.escalation.notifier import notify_operators


def _resp(status_code: int, text: str = ""):
    r = MagicMock()
    r.status_code = status_code
    r.text = text
    return r


@patch("app.escalation.notifier.httpx.post")
@patch("app.escalation.notifier.config")
def test_notify_operators_sends_email(mock_config, mock_post):
    mock_config.side_effect = lambda key, default=None: {
        "RESEND_API_KEY": "rk_test",
        "OPERATOR_EMAILS": "ops@example.com,sec@example.com",
        "FROM_EMAIL": "Cadidi <noreply@send.example.com>",
    }.get(key, default)
    mock_post.return_value = _resp(200)

    notify_operators(reason="VIP", user_message="I need help", phone_hash="abc123")

    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args.kwargs
    payload = call_kwargs["json"]
    assert payload["to"] == ["ops@example.com", "sec@example.com"]
    assert payload["from"] == "Cadidi <noreply@send.example.com>"
    assert "VIP" in payload["subject"]
    assert "I need help" in payload["text"]
    assert "abc123" in payload["text"]
    assert call_kwargs["headers"]["Authorization"] == "Bearer rk_test"


@patch("app.escalation.notifier.httpx.post")
@patch("app.escalation.notifier.config")
def test_notify_operators_skips_when_api_key_missing(mock_config, mock_post):
    mock_config.side_effect = lambda key, default=None: {
        "RESEND_API_KEY": "",
        "OPERATOR_EMAILS": "ops@example.com",
    }.get(key, default)

    notify_operators(reason="x", user_message="y", phone_hash="z")
    mock_post.assert_not_called()


@patch("app.escalation.notifier.httpx.post")
@patch("app.escalation.notifier.config")
def test_notify_operators_skips_when_no_recipients(mock_config, mock_post):
    mock_config.side_effect = lambda key, default=None: {
        "RESEND_API_KEY": "rk_test",
        "OPERATOR_EMAILS": "",
    }.get(key, default)

    notify_operators(reason="x", user_message="y", phone_hash="z")
    mock_post.assert_not_called()


@patch("app.escalation.notifier.httpx.post")
@patch("app.escalation.notifier.config")
def test_notify_operators_swallows_http_errors(mock_config, mock_post):
    mock_config.side_effect = lambda key, default=None: {
        "RESEND_API_KEY": "rk_test",
        "OPERATOR_EMAILS": "ops@example.com",
        "FROM_EMAIL": "Cadidi <noreply@send.example.com>",
    }.get(key, default)
    mock_post.side_effect = Exception("resend unreachable")

    # Must not raise.
    notify_operators(reason="x", user_message="y", phone_hash="z")


@patch("app.escalation.notifier.httpx.post")
@patch("app.escalation.notifier.config")
def test_notify_operators_logs_resend_4xx(mock_config, mock_post):
    mock_config.side_effect = lambda key, default=None: {
        "RESEND_API_KEY": "rk_test",
        "OPERATOR_EMAILS": "ops@example.com",
        "FROM_EMAIL": "Cadidi <noreply@send.example.com>",
    }.get(key, default)
    mock_post.return_value = _resp(422, '{"error":"invalid_from"}')

    # Must not raise even on 4xx.
    notify_operators(reason=None, user_message="y", phone_hash="z")


@patch("app.escalation.notifier.httpx.post")
@patch("app.escalation.notifier.config")
def test_notify_operators_handles_missing_reason(mock_config, mock_post):
    mock_config.side_effect = lambda key, default=None: {
        "RESEND_API_KEY": "rk_test",
        "OPERATOR_EMAILS": "ops@example.com",
        "FROM_EMAIL": "Cadidi <noreply@send.example.com>",
    }.get(key, default)
    mock_post.return_value = _resp(200)

    notify_operators(reason=None, user_message="hi", phone_hash="abc")

    payload = mock_post.call_args.kwargs["json"]
    assert "not provided" in payload["text"]
