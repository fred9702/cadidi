# KB Integration, Post-Opt-In Menu & Human Escalation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire up the campaign knowledge base into Claude's system prompt, add a post-opt-in topic menu, and build a human escalation system with operator response/resolve endpoints.

**Architecture:** KB markdown files are read at module load time and injected into the system prompt. Claude is instructed to prepend `[ESCALATE][REASON: ...]` when a human should take over. The backend detects this marker, logs to a `wa_escalations` table, and pauses bot responses until resolved. Operators use `/respond` and `/resolve` endpoints (same auth as `/broadcast`) to reply and close escalations.

**Tech Stack:** Python 3, FastAPI, Supabase (PostgreSQL), Anthropic Claude API, Twilio WhatsApp API

**Spec:** `docs/superpowers/specs/2026-04-09-kb-menu-escalation-design.md`

---

## File Structure

### New Files
| File | Responsibility |
|------|---------------|
| `app/escalation/__init__.py` | Package init |
| `app/escalation/detector.py` | Parse `[ESCALATE][REASON: ...]` from Claude response |
| `app/escalation/manager.py` | CRUD for `wa_escalations` table |
| `app/escalation/router.py` | `/respond` and `/resolve` FastAPI endpoints |
| `tests/escalation/__init__.py` | Test package init |
| `tests/escalation/test_detector.py` | Tests for detector |
| `tests/escalation/test_manager.py` | Tests for manager |
| `tests/escalation/test_router.py` | Tests for router endpoints |
| `supabase/migrations/20260409120000_create_wa_escalations.sql` | Table creation |

### Modified Files
| File | Change |
|------|--------|
| `app/ai/system_prompt.py` | Load KB files, fix OAFLAD name, add escalation instructions |
| `app/consent/messages.py` | Add `welcome_menu` and `escalation_holding` message types |
| `main.py` | Send menu on activate/rejoin, check open escalation, detect escalation in response, register escalation router |
| `tests/ai/test_system_prompt.py` | Update tests for new prompt content |

---

## Task 1: Supabase Migration — `wa_escalations` Table

**Files:**
- Create: `supabase/migrations/20260409120000_create_wa_escalations.sql`

- [ ] **Step 1: Write the migration**

```sql
-- Create escalation tracking table for human handoff.

CREATE TABLE wa_escalations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES wa_conversations(id),
    phone_hash TEXT NOT NULL,
    reason TEXT,
    user_message TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'resolved')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at TIMESTAMPTZ
);

CREATE INDEX idx_escalations_phone_status ON wa_escalations(phone_hash, status);
```

- [ ] **Step 2: Apply the migration locally**

Run: `supabase db push` (or apply via Supabase dashboard if remote-only)

- [ ] **Step 3: Commit**

```bash
git add supabase/migrations/20260409120000_create_wa_escalations.sql
git commit -m "feat: add wa_escalations table for human handoff tracking"
```

---

## Task 2: Escalation Detector

**Files:**
- Create: `app/escalation/__init__.py`
- Create: `app/escalation/detector.py`
- Create: `tests/escalation/__init__.py`
- Create: `tests/escalation/test_detector.py`

- [ ] **Step 1: Create package init files**

Create empty `app/escalation/__init__.py` and `tests/escalation/__init__.py`.

- [ ] **Step 2: Write failing tests for detector**

File: `tests/escalation/test_detector.py`

```python
from app.escalation.detector import parse_response


def test_parse_normal_response():
    result = parse_response("Hello, how can I help you?")
    assert result["escalated"] is False
    assert result["reason"] is None
    assert result["reply"] == "Hello, how can I help you?"


def test_parse_escalated_response_with_reason():
    raw = "[ESCALATE][REASON: VIP logistics request]I've notified the team. Someone will respond shortly."
    result = parse_response(raw)
    assert result["escalated"] is True
    assert result["reason"] == "VIP logistics request"
    assert result["reply"] == "I've notified the team. Someone will respond shortly."


def test_parse_escalated_response_without_reason():
    raw = "[ESCALATE]I've notified the team."
    result = parse_response(raw)
    assert result["escalated"] is True
    assert result["reason"] is None
    assert result["reply"] == "I've notified the team."


def test_parse_escalate_marker_case_insensitive():
    raw = "[escalate][REASON: test]Reply here."
    result = parse_response(raw)
    assert result["escalated"] is True
    assert result["reason"] == "test"
    assert result["reply"] == "Reply here."


def test_parse_escalate_not_at_start():
    raw = "Some text [ESCALATE] more text"
    result = parse_response(raw)
    assert result["escalated"] is False
    assert result["reply"] == "Some text [ESCALATE] more text"
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/escalation/test_detector.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.escalation.detector'`

- [ ] **Step 4: Implement the detector**

File: `app/escalation/detector.py`

```python
import re

_ESCALATE_PATTERN = re.compile(
    r"^\[escalate\](?:\[reason:\s*(.+?)\])?(.*)",
    re.IGNORECASE | re.DOTALL,
)


def parse_response(raw: str) -> dict:
    """Parse Claude's response for escalation markers.

    Returns dict with keys: escalated (bool), reason (str|None), reply (str).
    """
    match = _ESCALATE_PATTERN.match(raw.strip())
    if not match:
        return {"escalated": False, "reason": None, "reply": raw}
    reason = match.group(1)
    reply = match.group(2).strip()
    return {"escalated": True, "reason": reason, "reply": reply}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/escalation/test_detector.py -v`
Expected: All 5 tests PASS

- [ ] **Step 6: Commit**

```bash
git add app/escalation/__init__.py app/escalation/detector.py \
       tests/escalation/__init__.py tests/escalation/test_detector.py
git commit -m "feat: add escalation detector to parse [ESCALATE] marker from Claude responses"
```

---

## Task 3: Escalation Manager

**Files:**
- Create: `app/escalation/manager.py`
- Create: `tests/escalation/test_manager.py`

- [ ] **Step 1: Write failing tests for manager**

File: `tests/escalation/test_manager.py`

```python
from unittest.mock import MagicMock
from app.escalation.manager import create_escalation, get_open_escalation, resolve_escalation


def _mock_supabase():
    sb = MagicMock()
    return sb


def test_create_escalation_inserts_row():
    sb = _mock_supabase()
    sb.table.return_value.insert.return_value.execute.return_value = None

    create_escalation(
        sb,
        conversation_id="conv-123",
        phone_hash="hash-abc",
        reason="VIP request",
        user_message="I need help with my seat",
    )

    sb.table.assert_called_with("wa_escalations")
    insert_data = sb.table.return_value.insert.call_args[0][0]
    assert insert_data["conversation_id"] == "conv-123"
    assert insert_data["phone_hash"] == "hash-abc"
    assert insert_data["reason"] == "VIP request"
    assert insert_data["user_message"] == "I need help with my seat"
    assert insert_data["status"] == "open"


def test_get_open_escalation_returns_row():
    sb = _mock_supabase()
    row = {"id": "esc-1", "phone_hash": "hash-abc", "status": "open"}
    sb.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [row]

    result = get_open_escalation(sb, "hash-abc")
    assert result == row


def test_get_open_escalation_returns_none_when_empty():
    sb = _mock_supabase()
    sb.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []

    result = get_open_escalation(sb, "hash-abc")
    assert result is None


def test_resolve_escalation_updates_status():
    sb = _mock_supabase()
    sb.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = [{"id": "esc-1"}]

    result = resolve_escalation(sb, "hash-abc")
    assert result is True

    update_args = sb.table.return_value.update.call_args[0][0]
    assert update_args["status"] == "resolved"
    assert "resolved_at" in update_args


def test_resolve_escalation_returns_false_when_none_open():
    sb = _mock_supabase()
    sb.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = []

    result = resolve_escalation(sb, "hash-abc")
    assert result is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/escalation/test_manager.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.escalation.manager'`

- [ ] **Step 3: Implement the manager**

File: `app/escalation/manager.py`

```python
from datetime import datetime, timezone

from supabase import Client

ESCALATIONS_TABLE = "wa_escalations"


def create_escalation(
    supabase: Client,
    conversation_id: str,
    phone_hash: str,
    reason: str | None,
    user_message: str,
) -> None:
    """Insert a new open escalation."""
    supabase.table(ESCALATIONS_TABLE).insert({
        "conversation_id": conversation_id,
        "phone_hash": phone_hash,
        "reason": reason,
        "user_message": user_message,
        "status": "open",
    }).execute()


def get_open_escalation(supabase: Client, phone_hash: str) -> dict | None:
    """Return the open escalation for a phone_hash, or None."""
    result = (
        supabase.table(ESCALATIONS_TABLE)
        .select("*")
        .eq("phone_hash", phone_hash)
        .eq("status", "open")
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def resolve_escalation(supabase: Client, phone_hash: str) -> bool:
    """Resolve the open escalation for a phone_hash. Returns True if one was resolved."""
    now = datetime.now(timezone.utc).isoformat()
    result = (
        supabase.table(ESCALATIONS_TABLE)
        .update({"status": "resolved", "resolved_at": now})
        .eq("phone_hash", phone_hash)
        .eq("status", "open")
        .execute()
    )
    return len(result.data) > 0
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/escalation/test_manager.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add app/escalation/manager.py tests/escalation/test_manager.py
git commit -m "feat: add escalation manager for wa_escalations CRUD"
```

---

## Task 4: Escalation Router (`/respond` and `/resolve`)

**Files:**
- Create: `app/escalation/router.py`
- Create: `tests/escalation/test_router.py`

- [ ] **Step 1: Write failing tests for the router**

File: `tests/escalation/test_router.py`

```python
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


def _mock_supabase_with_conversation(conv_data=None):
    """Mock Supabase for conversation lookup and message insert."""
    sb = MagicMock()
    # get_or_create_conversation chain: .select().eq().eq().execute()
    conv_result = MagicMock()
    conv_result.data = [conv_data] if conv_data else []
    sb.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = conv_result
    sb.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = conv_result
    # insert chain
    sb.table.return_value.insert.return_value.execute.return_value = None
    # update chain (for resolve)
    update_result = MagicMock()
    update_result.data = [{"id": "esc-1"}] if conv_data else []
    sb.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = update_result
    return sb


@patch("app.twilio_client.send_whatsapp")
@patch("app.escalation.router.get_supabase")
@patch("app.broadcast.auth.config", return_value="valid-key")
def test_respond_sends_message(mock_config, mock_sb, mock_send):
    conv = {"id": "conv-123", "status": "active", "phone_hash": "abc"}
    mock_sb.return_value = _mock_supabase_with_conversation(conv)
    from main import app
    client = TestClient(app)
    response = client.post(
        "/respond",
        json={"phone": "+241060000001", "message": "We'll handle this for you."},
        headers={"Authorization": "Bearer valid-key"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "sent"
    mock_send.assert_called_once_with("+241060000001", "We'll handle this for you.")


@patch("app.escalation.router.get_supabase")
@patch("app.broadcast.auth.config", return_value="valid-key")
def test_respond_returns_404_no_conversation(mock_config, mock_sb):
    mock_sb.return_value = _mock_supabase_with_conversation(None)
    from main import app
    client = TestClient(app)
    response = client.post(
        "/respond",
        json={"phone": "+241060000001", "message": "Hello"},
        headers={"Authorization": "Bearer valid-key"},
    )
    assert response.status_code == 404


@patch("app.broadcast.auth.config", return_value="valid-key")
def test_respond_rejects_invalid_auth(mock_config):
    from main import app
    client = TestClient(app)
    response = client.post(
        "/respond",
        json={"phone": "+241060000001", "message": "Hello"},
        headers={"Authorization": "Bearer wrong-key"},
    )
    assert response.status_code == 401


@patch("app.broadcast.auth.config", return_value="valid-key")
def test_respond_rejects_missing_fields(mock_config):
    from main import app
    client = TestClient(app)
    response = client.post(
        "/respond",
        json={"phone": "+241060000001"},
        headers={"Authorization": "Bearer valid-key"},
    )
    assert response.status_code == 422


@patch("app.escalation.router.get_supabase")
@patch("app.broadcast.auth.config", return_value="valid-key")
def test_resolve_closes_escalation(mock_config, mock_sb):
    conv = {"id": "esc-1", "status": "open"}
    mock_sb.return_value = _mock_supabase_with_conversation(conv)
    from main import app
    client = TestClient(app)
    response = client.post(
        "/resolve",
        json={"phone": "+241060000001"},
        headers={"Authorization": "Bearer valid-key"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "resolved"


@patch("app.escalation.router.get_supabase")
@patch("app.broadcast.auth.config", return_value="valid-key")
def test_resolve_returns_404_no_open_escalation(mock_config, mock_sb):
    mock_sb.return_value = _mock_supabase_with_conversation(None)
    from main import app
    client = TestClient(app)
    response = client.post(
        "/resolve",
        json={"phone": "+241060000001"},
        headers={"Authorization": "Bearer valid-key"},
    )
    assert response.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/escalation/test_router.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.escalation.router'`

- [ ] **Step 3: Implement the router**

File: `app/escalation/router.py`

```python
import logging
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.supabase_client import get_supabase
from app.consent.hashing import hash_phone_number
from app.ai.conversations import get_or_create_conversation
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/escalation/test_router.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add app/escalation/router.py tests/escalation/test_router.py
git commit -m "feat: add /respond and /resolve endpoints for human escalation"
```

---

## Task 5: KB Integration + System Prompt Update

**Files:**
- Modify: `app/ai/system_prompt.py`
- Modify: `tests/ai/test_system_prompt.py`

KB files referenced (read at startup, not modified):
- `PROGRAMME_KB.md`
- `CAP241_KB.md`
- `BuildingResilience_KB.md`

- [ ] **Step 1: Write failing tests**

File: `tests/ai/test_system_prompt.py` — replace entire file:

```python
from app.ai.system_prompt import get_system_prompt


def test_system_prompt_contains_event_details():
    prompt = get_system_prompt("fr")
    assert "BuildingResilience" in prompt
    assert "17" in prompt
    assert "2026" in prompt
    assert "Libreville" in prompt
    assert "OAFLAD" in prompt


def test_system_prompt_french_instruction():
    prompt = get_system_prompt("fr")
    assert "français" in prompt.lower() or "french" in prompt.lower()


def test_system_prompt_english_instruction():
    prompt = get_system_prompt("en")
    assert "English" in prompt or "english" in prompt


def test_system_prompt_contains_kb_content():
    prompt = get_system_prompt("fr")
    # From PROGRAMME_KB.md
    assert "Cité de la Démocratie" in prompt
    # From CAP241_KB.md
    assert "CAP 241" in prompt
    assert "EQUILIBRES" in prompt
    # From BuildingResilience_KB.md
    assert "Fondation Ma Bannière" in prompt


def test_system_prompt_contains_escalation_instructions():
    prompt = get_system_prompt("fr")
    assert "[ESCALATE]" in prompt
    assert "[REASON:" in prompt


def test_system_prompt_correct_oaflad_name():
    prompt = get_system_prompt("fr")
    assert "Premières Dames" in prompt or "First Ladies" in prompt
```

- [ ] **Step 2: Run tests to verify the new ones fail**

Run: `pytest tests/ai/test_system_prompt.py -v`
Expected: `test_system_prompt_contains_kb_content`, `test_system_prompt_contains_escalation_instructions`, `test_system_prompt_correct_oaflad_name` FAIL

- [ ] **Step 3: Implement updated system_prompt.py**

File: `app/ai/system_prompt.py` — replace entire file:

```python
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

_KB_FILES = [
    "PROGRAMME_KB.md",
    "CAP241_KB.md",
    "BuildingResilience_KB.md",
]


def _load_kb() -> str:
    """Read all KB markdown files and concatenate their content."""
    sections = []
    for filename in _KB_FILES:
        path = _PROJECT_ROOT / filename
        if path.exists():
            sections.append(path.read_text(encoding="utf-8"))
    return "\n\n".join(sections)


_KB_CONTENT = _load_kb()

LANGUAGE_INSTRUCTIONS = {
    "fr": "Réponds toujours en français.",
    "en": "Always respond in English.",
}

SYSTEM_PROMPT_TEMPLATE = """\
You are the official AI assistant for #BuildingResilience, a high-level Pan-African \
conference organised by OAFLAD — Organisation des Premières Dames d'Afrique pour \
le Développement (Organization of African First Ladies for Development).

Event details:
- Date: 17 April 2026
- Location: Cité de la Démocratie, Libreville, Gabon
- Expected attendance: approximately 1,000 participants
- Theme: Building Resilience — strengthening the resilience of women and girls \
in the face of climate change and conflicts
- Under the high patronage of the President of the Gabonese Republic
- National launch of the #BuildingResilience campaign on National Women's Day

{language_instruction}

Tone and style:
- Professional, warm, and helpful
- Appropriate for a prestigious Pan-African conference
- Keep responses concise and WhatsApp-friendly (short paragraphs, no markdown)
- Use plain text with line breaks, no bullet points or formatting symbols

Scope:
- Answer questions about the #BuildingResilience event, campaign, CAP 241, \
OAFLAD, Fondation Ma Bannière, the EQUILIBRES programme, and the event schedule
- Use ONLY the knowledge base below to answer. Do not invent details
- If the information is not in the knowledge base, say so honestly and offer \
to connect the user with the organising team

Escalation:
- When you determine a human should handle this conversation, prepend \
[ESCALATE][REASON: brief reason] to your response
- Escalate when: VIP logistics requests, complaints, medical or security concerns, \
requests for personal contact with speakers or dignitaries, anything you cannot \
confidently answer from the knowledge base after informing the user
- Your response after the tags should be a natural message to the user \
acknowledging that the team has been notified
- Never reveal the [ESCALATE] or [REASON] tags to the user — they are internal markers

--- KNOWLEDGE BASE ---
{kb_content}
--- END KNOWLEDGE BASE ---\
"""


def get_system_prompt(language: str) -> str:
    """Return the system prompt with language-specific instruction and KB content."""
    lang_instruction = LANGUAGE_INSTRUCTIONS.get(
        language, LANGUAGE_INSTRUCTIONS["fr"]
    )
    return SYSTEM_PROMPT_TEMPLATE.format(
        language_instruction=lang_instruction,
        kb_content=_KB_CONTENT,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/ai/test_system_prompt.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add app/ai/system_prompt.py tests/ai/test_system_prompt.py
git commit -m "feat: inject KB content into system prompt, fix OAFLAD name, add escalation instructions"
```

---

## Task 6: Post-Opt-In Menu & Escalation Holding Messages

**Files:**
- Modify: `app/consent/messages.py`
- Modify: `tests/consent/test_messages.py`

- [ ] **Step 1: Read current test file**

Read `tests/consent/test_messages.py` to understand existing test patterns.

- [ ] **Step 2: Write failing tests for new message types**

Append to `tests/consent/test_messages.py`:

```python
def test_welcome_menu_french():
    msg = get_message("welcome_menu", "fr")
    assert "BuildingResilience" in msg
    assert "CAP 241" in msg
    assert "Fondation Ma Bannière" in msg or "Ma Bannière" in msg


def test_welcome_menu_english():
    msg = get_message("welcome_menu", "en")
    assert "BuildingResilience" in msg
    assert "CAP 241" in msg


def test_welcome_menu_falls_back_to_french():
    msg = get_message("welcome_menu", "xx")
    assert "BuildingResilience" in msg
    assert "CAP 241" in msg


def test_escalation_holding_french():
    msg = get_message("escalation_holding", "fr")
    assert "équipe" in msg.lower() or "equipe" in msg.lower()


def test_escalation_holding_english():
    msg = get_message("escalation_holding", "en")
    assert "team" in msg.lower()
```

- [ ] **Step 3: Run tests to verify new tests fail**

Run: `pytest tests/consent/test_messages.py -v`
Expected: New tests FAIL with `KeyError: 'welcome_menu'`

- [ ] **Step 4: Add new message types to messages.py**

Add to the `MESSAGES` dict in `app/consent/messages.py`:

```python
    "welcome_menu": {
        "fr": (
            "Bienvenue ! Je suis votre assistant IA pour "
            "#BuildingResilience.\n\n"
            "Comment puis-je vous aider ? Par exemple :\n"
            "1) La campagne #BuildingResilience\n"
            "2) Le cadre CAP 241\n"
            "3) La Fondation Ma Bannière\n"
            "4) Le programme de l'événement\n"
            "5) L'OAFLAD/OPDAD\n\n"
            "Vous pouvez aussi poser n'importe quelle question librement."
        ),
        "en": (
            "Welcome! I'm your AI assistant for "
            "#BuildingResilience.\n\n"
            "How can I help you? For example:\n"
            "1) The #BuildingResilience campaign\n"
            "2) The CAP 241 framework\n"
            "3) The Ma Bannière Foundation\n"
            "4) The event programme\n"
            "5) OAFLAD/OPDAD\n\n"
            "You can also ask any question freely."
        ),
    },
    "escalation_holding": {
        "fr": (
            "Votre demande est prise en charge par l'équipe organisatrice. "
            "Vous recevrez une réponse prochainement dans cette conversation."
        ),
        "en": (
            "Your request is being handled by the organising team. "
            "You'll receive a response shortly in this conversation."
        ),
    },
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/consent/test_messages.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add app/consent/messages.py tests/consent/test_messages.py
git commit -m "feat: add welcome_menu and escalation_holding message types"
```

---

## Task 7: Wire Everything Into `main.py`

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Update main.py**

Replace the entire content of `main.py`:

```python
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
from app.escalation.router import router as escalation_router
from app.escalation.detector import parse_response
from app.escalation.manager import create_escalation, get_open_escalation

import logging

logger = logging.getLogger(__name__)

app = FastAPI()
app.include_router(broadcast_router)
app.include_router(escalation_router)


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

            # Check for open escalation — skip Claude, send holding message
            if get_open_escalation(supabase, phone_hash):
                response_text = get_message("escalation_holding", lang)
            else:
                history = load_history(supabase, conv["id"])
                raw_response = get_ai_response(history, lang)
                parsed = parse_response(raw_response)

                if parsed["escalated"]:
                    create_escalation(
                        supabase,
                        conversation_id=conv["id"],
                        phone_hash=phone_hash,
                        reason=parsed["reason"],
                        user_message=Body,
                    )

                response_text = parsed["reply"]
                save_message(supabase, conv["id"], "assistant", response_text)
    elif result["action"] in ("activate", "rejoin"):
        state = resolve_consent_state(supabase, hash_phone_number(phone))
        lang = state.get("language_pref", "fr") if state else "fr"
        response_text = get_message("welcome_menu", lang)
    else:
        response_text = result["reply"]

    # Send reply via Twilio REST API
    send_whatsapp(phone, response_text)
    logger.info(f"Response to {phone[:6]}***: {result['action']}")
    return Response(status_code=200)


@app.get("/health")
async def health():
    return {"status": "ok"}
```

Key changes from the current `main.py`:
1. Import and register `escalation_router`
2. Import `parse_response`, `create_escalation`, `get_open_escalation`
3. In `forward_to_ai`: check for open escalation before calling Claude; parse Claude response for escalation marker after the call
4. `activate` and `rejoin` actions now send `welcome_menu` instead of `welcome_back`

- [ ] **Step 2: Run the full test suite**

Run: `pytest -v`
Expected: All tests PASS. If any existing tests relied on the old `activate` behavior (sending `welcome_back`), update them to expect `welcome_menu`.

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "feat: wire KB, escalation detection, holding messages, and welcome menu into request handler"
```

---

## Task 8: Integration Smoke Test

**Files:**
- No new files — manual verification

- [ ] **Step 1: Run full test suite**

Run: `pytest -v`
Expected: All tests PASS

- [ ] **Step 2: Start dev server and verify health**

Run: `uvicorn main:app --reload`
Expected: Server starts without import errors. Hit `GET /health` — returns `{"status": "ok"}`.

- [ ] **Step 3: Verify system prompt loads KB**

In a Python shell:
```python
from app.ai.system_prompt import get_system_prompt
prompt = get_system_prompt("fr")
assert "Cité de la Démocratie" in prompt
assert "[ESCALATE]" in prompt
print(f"System prompt length: {len(prompt)} chars")
```

- [ ] **Step 4: Commit any fixes if needed**

```bash
git add -A
git commit -m "fix: address integration issues from smoke testing"
```

(Skip this step if no fixes were needed.)
