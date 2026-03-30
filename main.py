from fastapi import FastAPI, Form, Request
from fastapi.responses import Response
from twilio.rest import Client
from decouple import config

from app.supabase_client import get_supabase
from app.consent.state_machine import process_message
from app.consent.messages import get_message
from app.consent.hashing import hash_phone_number
from app.consent.state_machine import resolve_consent_state

import logging

logger = logging.getLogger(__name__)

# Twilio config
account_sid = config("TWILIO_ACCOUNT_SID")
auth_token = config("TWILIO_AUTH_TOKEN")
twilio_number = config("TWILIO_WHATSAPP_NUMBER")
twilio_client = Client(account_sid, auth_token)

app = FastAPI()


def run_ai_query(message: str) -> str:
    """Placeholder for Claude AI integration (WA-B04). Returns AI response."""
    return f"[AI placeholder] You asked: {message}"


def send_whatsapp(to: str, body: str) -> None:
    """Send a WhatsApp message via Twilio REST API."""
    twilio_client.messages.create(
        from_=f"whatsapp:{twilio_number}",
        to=f"whatsapp:{to}",
        body=body,
    )


@app.post("/message")
async def reply(request: Request, Body: str = Form()):
    form_data = await request.form()
    phone = form_data["From"].split("whatsapp:")[-1]

    supabase = get_supabase()
    result = process_message(supabase, phone, Body)

    # Determine response text
    if result["action"] == "forward_to_ai":
        response_text = run_ai_query(Body)
    elif result["action"] == "activate":
        state = resolve_consent_state(supabase, hash_phone_number(phone))
        lang = state.get("language_pref", "fr") if state else "fr"
        response_text = get_message("welcome_back", lang)
    else:
        response_text = result["reply"]

    # Send reply via Twilio REST API
    send_whatsapp(phone, response_text)
    logger.info(f"Response to {phone[:6]}***: {result['action']}")
    return Response(status_code=200)


@app.get("/health")
async def health():
    return {"status": "ok"}
