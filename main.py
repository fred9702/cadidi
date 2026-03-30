from fastapi import FastAPI, Form, Request
from fastapi.responses import PlainTextResponse
from twilio.twiml.messaging_response import MessagingResponse
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
twilio_number = config("TWILIO_NUMBER")

app = FastAPI()


def run_ai_query(message: str) -> str:
    """Placeholder for Claude AI integration (WA-B04). Returns AI response."""
    return f"[AI placeholder] You asked: {message}"


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
        # User just consented — send welcome-back in their language
        state = resolve_consent_state(supabase, hash_phone_number(phone))
        lang = state.get("language_pref", "fr") if state else "fr"
        response_text = get_message("welcome_back", lang)
    else:
        response_text = result["reply"]

    # Build Twilio XML response
    twilio_response = MessagingResponse()
    twilio_response.message(response_text)
    xml = str(twilio_response)
    logger.info(f"Response to {phone[:6]}***: {result['action']}")
    return PlainTextResponse(xml, media_type="application/xml")


@app.get("/health")
async def health():
    return {"status": "ok"}
