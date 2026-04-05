import logging
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.supabase_client import get_supabase
import app.twilio_client as twilio_client
from app.broadcast.auth import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter()

REGISTRATIONS_TABLE = "registrations"


class BroadcastRequest(BaseModel):
    message: Optional[str] = None
    language: Optional[str] = None


@router.post("/broadcast")
async def broadcast(
    body: BroadcastRequest,
    authorization: Optional[str] = Header(None),
):
    """Send a WhatsApp message to all active (consented) participants.

    Requires Bearer token authentication via the Authorization header.
    Optionally filter recipients by language_pref.
    """
    # Validate auth
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization")
    token = authorization[len("Bearer "):]
    if not verify_api_key(token):
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Validate body
    if not body.message:
        raise HTTPException(status_code=400, detail="Missing message field")

    # Query recipients
    supabase = get_supabase()
    query = (
        supabase.table(REGISTRATIONS_TABLE)
        .select("phone")
        .eq("consent_status", "active")
        .neq("phone", None)
    )
    if body.language:
        query = query.eq("language_pref", body.language)
    result = query.execute()

    # Send messages
    sent = 0
    failed = 0
    for row in result.data:
        try:
            twilio_client.send_whatsapp(row["phone"], body.message)
            sent += 1
        except Exception:
            failed += 1
            logger.exception("Broadcast send failed for a recipient")

    return {"sent": sent, "failed": failed}
