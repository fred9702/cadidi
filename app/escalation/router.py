import logging
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.supabase_client import get_supabase
from app.consent.hashing import hash_phone_number
from app.ai.history import save_message
from app.escalation.manager import resolve_escalation
import app.twilio_client as twilio_client
from app.broadcast.auth import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter()


class RespondRequest(BaseModel):
    phone: str
    message: str


class ResolveRequest(BaseModel):
    phone: str


def _validate_auth(authorization: Optional[str]) -> None:
    """Validate Bearer token. Raises HTTPException on failure."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization")
    token = authorization[len("Bearer "):]
    if not verify_api_key(token):
        raise HTTPException(status_code=401, detail="Invalid API key")


@router.post("/respond")
async def respond(
    body: RespondRequest,
    authorization: Optional[str] = Header(None),
):
    """Send a human operator's reply to a user's WhatsApp conversation."""
    _validate_auth(authorization)

    supabase = get_supabase()
    phone_hash = hash_phone_number(body.phone)

    # Look up active conversation
    result = (
        supabase.table("wa_conversations")
        .select("*")
        .eq("phone_hash", phone_hash)
        .eq("status", "active")
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="No active conversation for this phone number")

    conv = result.data[0]

    # Save to message history as "assistant" for Claude continuity
    save_message(supabase, conv["id"], "assistant", body.message)

    # Send via Twilio
    twilio_client.send_whatsapp(body.phone, body.message)
    logger.info(f"Human response sent to {body.phone[:6]}***")

    return {"status": "sent"}


@router.post("/resolve")
async def resolve(
    body: ResolveRequest,
    authorization: Optional[str] = Header(None),
):
    """Resolve (close) an open escalation, returning the user to the bot."""
    _validate_auth(authorization)

    supabase = get_supabase()
    phone_hash = hash_phone_number(body.phone)

    resolved = resolve_escalation(supabase, phone_hash)
    if not resolved:
        raise HTTPException(status_code=404, detail="No open escalation for this phone number")

    logger.info(f"Escalation resolved for {body.phone[:6]}***")
    return {"status": "resolved"}
