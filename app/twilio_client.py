from twilio.rest import Client
from decouple import config

_account_sid = config("TWILIO_ACCOUNT_SID")
_auth_token = config("TWILIO_AUTH_TOKEN")
_messaging_service_sid = config("TWILIO_MESSAGING_SERVICE_SID")
_twilio_client = Client(_account_sid, _auth_token)


def send_whatsapp(to: str, body: str) -> None:
    """Send a WhatsApp message via Twilio Messaging Service."""
    _twilio_client.messages.create(
        messaging_service_sid=_messaging_service_sid,
        to=f"whatsapp:{to}",
        body=body,
    )
