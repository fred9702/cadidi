from fastapi import FastAPI, Form, Request
from fastapi.responses import Response

from app.supabase_client import get_supabase
from app.twilio_client import send_whatsapp
from app.consent.state_machine import process_message
from app.consent.messages import get_message
from app.consent.hashing import hash_phone_number
from app.consent.state_machine import resolve_consent_state
from app.ai.conversations import get_or_create_conversation
from app.ai.history import save_message, load_history
from app.ai.client import get_ai_response
from app.rate_limit import check_rate_limit, rate_limit_message
from app.broadcast.router import router as broadcast_router

import logging

logger = logging.getLogger(__name__)

app = FastAPI()
app.include_router(broadcast_router)


@app.post("/message")
async def reply(request: Request, Body: str = Form()):
    form_data = await request.form()
    phone = form_data["From"].split("whatsapp:")[-1]

    supabase = get_supabase()
    result = process_message(supabase, phone, Body)

    # Determine response text
    if result["action"] == "forward_to_ai":
        phone_hash = hash_phone_number(phone)
        lang = result["language"]

        # Rate limit check — before calling Claude API
        if not check_rate_limit(phone_hash):
            response_text = rate_limit_message(lang)
        else:
            conv = get_or_create_conversation(supabase, phone_hash, lang)
            save_message(supabase, conv["id"], "user", Body)
            history = load_history(supabase, conv["id"])
            response_text = get_ai_response(history, lang)
            save_message(supabase, conv["id"], "assistant", response_text)
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
