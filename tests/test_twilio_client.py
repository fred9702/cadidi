from unittest.mock import patch, MagicMock


@patch("app.twilio_client._twilio_client")
def test_send_whatsapp_calls_twilio(mock_client):
    from app.twilio_client import send_whatsapp
    send_whatsapp("+447700900000", "Hello")
    mock_client.messages.create.assert_called_once()
    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["to"] == "whatsapp:+447700900000"
    assert call_kwargs["body"] == "Hello"


@patch("app.twilio_client._twilio_client")
def test_send_whatsapp_uses_messaging_service(mock_client):
    from app.twilio_client import send_whatsapp
    send_whatsapp("+447700900000", "Test")
    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert "messaging_service_sid" in call_kwargs
