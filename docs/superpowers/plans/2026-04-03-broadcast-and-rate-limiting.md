# Broadcast Endpoint & Per-User Rate Limiting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an authenticated broadcast endpoint for sending announcements to consented participants, and per-user rate limiting to protect the Claude API from abuse.

**Architecture:** Extract Twilio helpers to a shared module. Add broadcast as a FastAPI sub-router with API key auth. Add in-memory sliding window rate limiter as a standalone module. Wire both into main.py.

**Tech Stack:** FastAPI, Supabase, Twilio, python-decouple (no new dependencies)

---

## File Map

| Action | File | Responsibility |
|---|---|---|
| Create | `app/twilio_client.py` | Shared Twilio client + `send_whatsapp` |
| Create | `app/broadcast/__init__.py` | Package init |
| Create | `app/broadcast/auth.py` | API key validation |
| Create | `app/broadcast/router.py` | POST /broadcast endpoint |
| Create | `app/rate_limit.py` | In-memory per-user rate limiter |
| Modify | `main.py` | Remove Twilio config, import from shared module, add rate limiting, register broadcast router |
| Modify | `tests/conftest.py` | Add BROADCAST_API_KEY dummy |
| Modify | `tests/consent/test_integration.py` | Update send_whatsapp mock path |
| Create | `tests/test_twilio_client.py` | Tests for shared Twilio module |
| Create | `tests/broadcast/__init__.py` | Test package |
| Create | `tests/broadcast/test_auth.py` | Auth tests |
| Create | `tests/broadcast/test_router.py` | Broadcast endpoint tests |
| Create | `tests/test_rate_limit.py` | Rate limiter tests |

---

### Task 1: Extract Twilio Client to Shared Module

**Files:**
- Create: `app/twilio_client.py`
- Create: `tests/test_twilio_client.py`
- Modify: `main.py`
- Modify: `tests/consent/test_integration.py`

- [ ] **Step 1: Write failing test for the shared Twilio module**

Create `tests/test_twilio_client.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/home/chomei/bomalab/cadidi/.venv/bin/python -m pytest tests/test_twilio_client.py -v`
Expected: FAIL with ModuleNotFoundError or ImportError

- [ ] **Step 3: Create app/twilio_client.py**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/home/chomei/bomalab/cadidi/.venv/bin/python -m pytest tests/test_twilio_client.py -v`
Expected: Both tests PASS

- [ ] **Step 5: Update main.py to import from shared module**

Replace the Twilio config block and `send_whatsapp` function in `main.py`. The full updated `main.py`:

```python
from fastapi import FastAPI, Form, Request
from fastapi.responses import Response
from decouple import config

from app.supabase_client import get_supabase
from app.twilio_client import send_whatsapp
from app.consent.state_machine import process_message
from app.consent.messages import get_message
from app.consent.hashing import hash_phone_number
from app.consent.state_machine import resolve_consent_state
from app.ai.conversations import get_or_create_conversation
from app.ai.history import save_message, load_history
from app.ai.client import get_ai_response

import logging

logger = logging.getLogger(__name__)

app = FastAPI()


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
```

- [ ] **Step 6: Update integration tests to mock new path**

In `tests/consent/test_integration.py`, replace all occurrences of `"main.send_whatsapp"` with `"app.twilio_client.send_whatsapp"`. There are 4 patches to update:

- `test_unknown_sender_gets_rejection`: `@patch("app.twilio_client.send_whatsapp")`
- `test_registered_sender_gets_consent_prompt`: `@patch("app.twilio_client.send_whatsapp")`
- `test_active_sender_gets_ai_response`: `@patch("app.twilio_client.send_whatsapp")`
- `test_active_sender_opts_out`: `@patch("app.twilio_client.send_whatsapp")`

- [ ] **Step 7: Run full test suite**

Run: `/home/chomei/bomalab/cadidi/.venv/bin/python -m pytest -v`
Expected: All tests PASS

- [ ] **Step 8: Commit**

```bash
git add app/twilio_client.py tests/test_twilio_client.py main.py tests/consent/test_integration.py
git commit -m "refactor: extract Twilio client to shared module

Move send_whatsapp and Twilio configuration from main.py to
app/twilio_client.py so the broadcast router can reuse it
without circular imports. Update integration test mock paths."
```

---

### Task 2: Rate Limiter Module

**Files:**
- Create: `tests/test_rate_limit.py`
- Create: `app/rate_limit.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_rate_limit.py`:

```python
import time
from unittest.mock import patch

from app.rate_limit import (
    check_rate_limit,
    rate_limit_message,
    RATE_LIMIT_MAX_MESSAGES,
    RATE_LIMIT_WINDOW_SECONDS,
    _message_log,
)


def setup_function():
    """Clear rate limit state before each test."""
    _message_log.clear()


def test_allows_first_message():
    assert check_rate_limit("hash1") is True


def test_allows_up_to_max_messages():
    for i in range(RATE_LIMIT_MAX_MESSAGES):
        assert check_rate_limit("hash1") is True


def test_blocks_after_max_messages():
    for i in range(RATE_LIMIT_MAX_MESSAGES):
        check_rate_limit("hash1")
    assert check_rate_limit("hash1") is False


def test_different_users_have_separate_limits():
    for i in range(RATE_LIMIT_MAX_MESSAGES):
        check_rate_limit("hash1")
    assert check_rate_limit("hash1") is False
    assert check_rate_limit("hash2") is True


def test_allows_after_window_expires():
    past = time.time() - RATE_LIMIT_WINDOW_SECONDS - 1
    _message_log["hash1"] = [past] * RATE_LIMIT_MAX_MESSAGES
    assert check_rate_limit("hash1") is True


def test_rate_limit_message_french():
    msg = rate_limit_message("fr")
    assert "trop rapidement" in msg


def test_rate_limit_message_english():
    msg = rate_limit_message("en")
    assert "too quickly" in msg


def test_rate_limit_message_unknown_falls_back_to_french():
    msg = rate_limit_message("xx")
    assert "trop rapidement" in msg


def test_constants():
    assert RATE_LIMIT_MAX_MESSAGES == 10
    assert RATE_LIMIT_WINDOW_SECONDS == 60
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/home/chomei/bomalab/cadidi/.venv/bin/python -m pytest tests/test_rate_limit.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Implement rate_limit.py**

Create `app/rate_limit.py`:

```python
import time

RATE_LIMIT_MAX_MESSAGES = 10
RATE_LIMIT_WINDOW_SECONDS = 60

_message_log: dict[str, list[float]] = {}

RATE_LIMIT_MESSAGES = {
    "fr": (
        "Vous envoyez des messages trop rapidement. "
        "Veuillez patienter un moment avant de réessayer."
    ),
    "en": (
        "You're sending messages too quickly. "
        "Please wait a moment before trying again."
    ),
}


def check_rate_limit(phone_hash: str) -> bool:
    """Check if a user is within their rate limit.

    Returns True if allowed, False if rate-limited.
    Uses an in-memory sliding window: up to RATE_LIMIT_MAX_MESSAGES
    messages per RATE_LIMIT_WINDOW_SECONDS per user.
    """
    now = time.time()
    cutoff = now - RATE_LIMIT_WINDOW_SECONDS

    timestamps = _message_log.get(phone_hash, [])
    timestamps = [t for t in timestamps if t > cutoff]

    if len(timestamps) >= RATE_LIMIT_MAX_MESSAGES:
        _message_log[phone_hash] = timestamps
        return False

    timestamps.append(now)
    _message_log[phone_hash] = timestamps
    return True


def rate_limit_message(language: str) -> str:
    """Return a polite rate-limit message in the user's language."""
    return RATE_LIMIT_MESSAGES.get(language, RATE_LIMIT_MESSAGES["fr"])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/home/chomei/bomalab/cadidi/.venv/bin/python -m pytest tests/test_rate_limit.py -v`
Expected: All 9 tests PASS

- [ ] **Step 5: Commit**

```bash
git add app/rate_limit.py tests/test_rate_limit.py
git commit -m "feat: add per-user rate limiting with sliding window

In-memory rate limiter that allows up to 10 messages per 60 seconds
per user (by phone_hash). Provides bilingual rate-limit messages
(FR/EN). Protects Claude API from abuse and runaway costs."
```

---

### Task 3: Broadcast Auth Module

**Files:**
- Create: `app/broadcast/__init__.py`
- Create: `app/broadcast/auth.py`
- Create: `tests/broadcast/__init__.py`
- Create: `tests/broadcast/test_auth.py`
- Modify: `tests/conftest.py`

- [ ] **Step 1: Add BROADCAST_API_KEY to conftest**

In `tests/conftest.py`, add after the existing `os.environ.setdefault` lines:

```python
os.environ.setdefault("BROADCAST_API_KEY", "test_broadcast_key")
```

- [ ] **Step 2: Write failing tests**

Create `tests/broadcast/__init__.py` (empty) and `tests/broadcast/test_auth.py`:

```python
from unittest.mock import patch

from app.broadcast.auth import verify_api_key


@patch("app.broadcast.auth.config", return_value="correct-secret-key")
def test_verify_valid_key(mock_config):
    assert verify_api_key("correct-secret-key") is True


@patch("app.broadcast.auth.config", return_value="correct-secret-key")
def test_verify_invalid_key(mock_config):
    assert verify_api_key("wrong-key") is False


@patch("app.broadcast.auth.config", return_value="correct-secret-key")
def test_verify_empty_key(mock_config):
    assert verify_api_key("") is False


@patch("app.broadcast.auth.config", return_value="correct-secret-key")
def test_verify_timing_safe(mock_config):
    """Verify we use secrets.compare_digest (timing-safe comparison)."""
    import secrets
    with patch("app.broadcast.auth.secrets.compare_digest", wraps=secrets.compare_digest) as mock_compare:
        verify_api_key("some-key")
        mock_compare.assert_called_once()
```

- [ ] **Step 3: Run test to verify it fails**

Run: `/home/chomei/bomalab/cadidi/.venv/bin/python -m pytest tests/broadcast/test_auth.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 4: Implement auth.py**

Create `app/broadcast/__init__.py` (empty) and `app/broadcast/auth.py`:

```python
import secrets

from decouple import config


def verify_api_key(api_key: str) -> bool:
    """Validate a broadcast API key using timing-safe comparison.

    Compares against the BROADCAST_API_KEY environment variable.
    Returns True if valid, False otherwise.
    """
    expected = config("BROADCAST_API_KEY")
    return secrets.compare_digest(api_key, expected)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `/home/chomei/bomalab/cadidi/.venv/bin/python -m pytest tests/broadcast/test_auth.py -v`
Expected: All 4 tests PASS

- [ ] **Step 6: Commit**

```bash
git add app/broadcast/__init__.py app/broadcast/auth.py tests/broadcast/__init__.py tests/broadcast/test_auth.py tests/conftest.py
git commit -m "feat: add broadcast API key authentication

Timing-safe bearer token validation using secrets.compare_digest.
BROADCAST_API_KEY env var must be set on Railway for production use."
```

---

### Task 4: Broadcast Router

**Files:**
- Create: `app/broadcast/router.py`
- Create: `tests/broadcast/test_router.py`

- [ ] **Step 1: Write failing tests**

Create `tests/broadcast/test_router.py`:

```python
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


def _mock_supabase_with_recipients(rows):
    """Mock Supabase returning recipient rows from registrations."""
    sb = MagicMock()
    # Chain: .select().eq().neq().execute() or .select().eq().neq().eq().execute()
    chain = sb.table.return_value.select.return_value
    chain.eq.return_value.neq.return_value.execute.return_value.data = rows
    chain.eq.return_value.neq.return_value.eq.return_value.execute.return_value.data = rows
    return sb


@patch("app.twilio_client.send_whatsapp")
@patch("app.broadcast.router.get_supabase")
@patch("app.broadcast.auth.config", return_value="valid-key")
def test_broadcast_sends_to_active_users(mock_config, mock_sb, mock_send):
    mock_sb.return_value = _mock_supabase_with_recipients([
        {"phone": "+447700900001"},
        {"phone": "+447700900002"},
    ])
    from main import app
    client = TestClient(app)
    response = client.post(
        "/broadcast",
        json={"message": "Hello everyone!"},
        headers={"Authorization": "Bearer valid-key"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["sent"] == 2
    assert data["failed"] == 0


@patch("app.twilio_client.send_whatsapp")
@patch("app.broadcast.router.get_supabase")
@patch("app.broadcast.auth.config", return_value="valid-key")
def test_broadcast_with_language_filter(mock_config, mock_sb, mock_send):
    mock_sb.return_value = _mock_supabase_with_recipients([
        {"phone": "+447700900001"},
    ])
    from main import app
    client = TestClient(app)
    response = client.post(
        "/broadcast",
        json={"message": "Bonjour!", "language": "fr"},
        headers={"Authorization": "Bearer valid-key"},
    )
    assert response.status_code == 200
    assert response.json()["sent"] == 1


@patch("app.broadcast.auth.config", return_value="valid-key")
def test_broadcast_rejects_invalid_key(mock_config):
    from main import app
    client = TestClient(app)
    response = client.post(
        "/broadcast",
        json={"message": "Hello"},
        headers={"Authorization": "Bearer wrong-key"},
    )
    assert response.status_code == 401


@patch("app.broadcast.auth.config", return_value="valid-key")
def test_broadcast_rejects_missing_auth(mock_config):
    from main import app
    client = TestClient(app)
    response = client.post("/broadcast", json={"message": "Hello"})
    assert response.status_code == 401


@patch("app.broadcast.auth.config", return_value="valid-key")
def test_broadcast_rejects_missing_message(mock_config):
    from main import app
    client = TestClient(app)
    response = client.post(
        "/broadcast",
        json={},
        headers={"Authorization": "Bearer valid-key"},
    )
    assert response.status_code == 400


@patch("app.twilio_client.send_whatsapp")
@patch("app.broadcast.router.get_supabase")
@patch("app.broadcast.auth.config", return_value="valid-key")
def test_broadcast_counts_failures(mock_config, mock_sb, mock_send):
    mock_sb.return_value = _mock_supabase_with_recipients([
        {"phone": "+447700900001"},
        {"phone": "+447700900002"},
    ])
    mock_send.side_effect = [None, Exception("Twilio error")]
    from main import app
    client = TestClient(app)
    response = client.post(
        "/broadcast",
        json={"message": "Hello"},
        headers={"Authorization": "Bearer valid-key"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["sent"] == 1
    assert data["failed"] == 1


@patch("app.twilio_client.send_whatsapp")
@patch("app.broadcast.router.get_supabase")
@patch("app.broadcast.auth.config", return_value="valid-key")
def test_broadcast_zero_recipients(mock_config, mock_sb, mock_send):
    mock_sb.return_value = _mock_supabase_with_recipients([])
    from main import app
    client = TestClient(app)
    response = client.post(
        "/broadcast",
        json={"message": "Hello"},
        headers={"Authorization": "Bearer valid-key"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["sent"] == 0
    assert data["failed"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/home/chomei/bomalab/cadidi/.venv/bin/python -m pytest tests/broadcast/test_router.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Implement router.py**

Create `app/broadcast/router.py`:

```python
import logging
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.supabase_client import get_supabase
from app.twilio_client import send_whatsapp
from app.broadcast.auth import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter()

REGISTRATIONS_TABLE = "registrations"


class BroadcastRequest(BaseModel):
    message: str
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
            send_whatsapp(row["phone"], body.message)
            sent += 1
        except Exception:
            failed += 1
            logger.exception("Broadcast send failed for a recipient")

    return {"sent": sent, "failed": failed}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/home/chomei/bomalab/cadidi/.venv/bin/python -m pytest tests/broadcast/test_router.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add app/broadcast/router.py tests/broadcast/test_router.py
git commit -m "feat: add broadcast endpoint for sending announcements

POST /broadcast with Bearer token auth sends a WhatsApp message
to all active (consented) participants. Supports optional language
filtering for targeted bilingual announcements. Individual send
failures are counted but don't abort the broadcast."
```

---

### Task 5: Wire Rate Limiting and Broadcast Into main.py

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Add rate limiting and broadcast router to main.py**

Update `main.py` to the following:

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
```

- [ ] **Step 2: Run full test suite**

Run: `/home/chomei/bomalab/cadidi/.venv/bin/python -m pytest -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "feat: wire rate limiting and broadcast router into main app

Rate limiting (10 msgs/60s per user) now gates the forward_to_ai
path, protecting Claude API from abuse. Consent messages (OUI, STOP,
etc.) are never rate-limited. Broadcast router registered at
POST /broadcast for admin announcements."
```

---

### Task 6: Update .env.example and Final Verification

**Files:**
- Modify: `.env.example`

- [ ] **Step 1: Add BROADCAST_API_KEY to .env.example**

Add to `.env.example` after the Anthropic section:

```
# Broadcast
BROADCAST_API_KEY=
```

- [ ] **Step 2: Run full test suite**

Run: `/home/chomei/bomalab/cadidi/.venv/bin/python -m pytest -v`
Expected: All tests PASS

- [ ] **Step 3: Verify all imports**

Run: `/home/chomei/bomalab/cadidi/.venv/bin/python -c "from app.twilio_client import send_whatsapp; from app.rate_limit import check_rate_limit, rate_limit_message; from app.broadcast.router import router; from app.broadcast.auth import verify_api_key; print('All imports OK')"`
Expected: `All imports OK`

- [ ] **Step 4: Commit**

```bash
git add .env.example
git commit -m "chore: add BROADCAST_API_KEY to .env.example

Documents the new environment variable required for the
broadcast endpoint authentication."
```
