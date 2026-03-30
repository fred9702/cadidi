# Opt-In Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement an explicit consent-based opt-in flow that gates access to the WhatsApp AI assistant behind phone number verification and RGPD-compliant consent.

**Architecture:** Webhook-only approach. Every incoming message is routed through a state machine: hash the sender phone → look up in Supabase registration table → route based on consent_status (unknown/registered/active/opted_out). Consent captured via trigger keywords in 4 languages. No RAG — this is pre-AI-assistant gating logic.

**Tech Stack:** Python 3.10+, FastAPI, supabase-py, hashlib (stdlib), pytest

**Spec:** `docs/superpowers/specs/2026-03-30-opt-in-flow-design.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `app/consent/__init__.py` | Create | Package init |
| `app/consent/messages.py` | Create | All message templates (4 languages x 5 message types) |
| `app/consent/triggers.py` | Create | Trigger word sets and matching logic |
| `app/consent/state_machine.py` | Create | State lookup, transitions, Supabase queries |
| `app/consent/hashing.py` | Create | SHA-256 phone number hashing |
| `app/supabase_client.py` | Create | Supabase client initialisation |
| `tests/consent/__init__.py` | Create | Package init |
| `tests/consent/test_hashing.py` | Create | Tests for phone hashing |
| `tests/consent/test_triggers.py` | Create | Tests for trigger word matching |
| `tests/consent/test_messages.py` | Create | Tests for message template retrieval |
| `tests/consent/test_state_machine.py` | Create | Tests for state transitions |
| `tests/consent/test_integration.py` | Create | End-to-end webhook test with mocked Supabase |
| `main.py` | Modify | Refactor `/message` endpoint to use consent state machine |
| `requirements.txt` | Modify | Add supabase, pytest |

---

### Task 1: Project setup — add dependencies and test framework

**Files:**
- Modify: `requirements.txt`
- Create: `app/__init__.py`
- Create: `app/consent/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/consent/__init__.py`
- Create: `pytest.ini`

- [ ] **Step 1: Add supabase and pytest to requirements.txt**

Append to the end of `requirements.txt`:
```
supabase
pytest
pytest-asyncio
httpx
```

- [ ] **Step 2: Create package directories and init files**

```bash
mkdir -p app/consent tests/consent
touch app/__init__.py app/consent/__init__.py tests/__init__.py tests/consent/__init__.py
```

- [ ] **Step 3: Create pytest.ini**

Create `pytest.ini`:
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_functions = test_*
```

- [ ] **Step 4: Install dependencies**

```bash
pip install supabase pytest pytest-asyncio httpx
```

- [ ] **Step 5: Verify pytest runs**

```bash
pytest --co
```
Expected: `no tests ran` (no test files with tests yet), no import errors.

- [ ] **Step 6: Commit**

```bash
git add requirements.txt app/ tests/ pytest.ini
git commit -m "feat: add project structure, supabase and pytest dependencies"
```

---

### Task 2: Phone number hashing

**Files:**
- Create: `tests/consent/test_hashing.py`
- Create: `app/consent/hashing.py`

- [ ] **Step 1: Write the failing test**

Create `tests/consent/test_hashing.py`:
```python
from app.consent.hashing import hash_phone_number


def test_hash_phone_number_returns_sha256():
    result = hash_phone_number("+447700900000")
    # SHA-256 produces 64 hex characters
    assert len(result) == 64
    assert result.isalnum()


def test_hash_phone_number_is_deterministic():
    a = hash_phone_number("+447700900000")
    b = hash_phone_number("+447700900000")
    assert a == b


def test_hash_phone_number_different_numbers_differ():
    a = hash_phone_number("+447700900000")
    b = hash_phone_number("+447700900001")
    assert a != b


def test_hash_phone_number_strips_whitespace():
    a = hash_phone_number("+447700900000")
    b = hash_phone_number(" +447700900000 ")
    assert a == b
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/consent/test_hashing.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'app.consent.hashing'`

- [ ] **Step 3: Write minimal implementation**

Create `app/consent/hashing.py`:
```python
import hashlib


def hash_phone_number(phone: str) -> str:
    """SHA-256 hash of a phone number. Strips whitespace before hashing."""
    return hashlib.sha256(phone.strip().encode("utf-8")).hexdigest()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/consent/test_hashing.py -v
```
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add app/consent/hashing.py tests/consent/test_hashing.py
git commit -m "feat: add SHA-256 phone number hashing"
```

---

### Task 3: Trigger word matching

**Files:**
- Create: `tests/consent/test_triggers.py`
- Create: `app/consent/triggers.py`

- [ ] **Step 1: Write the failing test**

Create `tests/consent/test_triggers.py`:
```python
from app.consent.triggers import match_trigger


def test_consent_yes_en():
    assert match_trigger("YES") == "consent"


def test_consent_oui_fr():
    assert match_trigger("oui") == "consent"


def test_consent_si_es():
    assert match_trigger("SÍ") == "consent"


def test_consent_si_no_accent_es():
    assert match_trigger("si") == "consent"


def test_consent_sim_pt():
    assert match_trigger("Sim") == "consent"


def test_opt_out_stop():
    assert match_trigger("STOP") == "opt_out"


def test_opt_out_arreter_fr():
    assert match_trigger("arrêter") == "opt_out"


def test_opt_out_arreter_no_accent_fr():
    assert match_trigger("ARRETER") == "opt_out"


def test_opt_out_parar():
    assert match_trigger("parar") == "opt_out"


def test_rejoin_en():
    assert match_trigger("join") == "rejoin"


def test_rejoin_fr():
    assert match_trigger("REJOINDRE") == "rejoin"


def test_rejoin_es():
    assert match_trigger("unirse") == "rejoin"


def test_rejoin_pt():
    assert match_trigger("juntar") == "rejoin"


def test_no_match_random_text():
    assert match_trigger("hello") is None


def test_no_match_empty_string():
    assert match_trigger("") is None


def test_match_with_whitespace():
    assert match_trigger("  yes  ") == "consent"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/consent/test_triggers.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'app.consent.triggers'`

- [ ] **Step 3: Write minimal implementation**

Create `app/consent/triggers.py`:
```python
CONSENT_WORDS = {"yes", "oui", "si", "sí", "sim"}
OPT_OUT_WORDS = {"stop", "arrêter", "arreter", "parar"}
REJOIN_WORDS = {"join", "rejoindre", "unirse", "juntar"}


def match_trigger(text: str) -> str | None:
    """Match a message against trigger words. Returns 'consent', 'opt_out', 'rejoin', or None."""
    normalized = text.strip().lower()
    if normalized in CONSENT_WORDS:
        return "consent"
    if normalized in OPT_OUT_WORDS:
        return "opt_out"
    if normalized in REJOIN_WORDS:
        return "rejoin"
    return None
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/consent/test_triggers.py -v
```
Expected: 18 passed.

- [ ] **Step 5: Commit**

```bash
git add app/consent/triggers.py tests/consent/test_triggers.py
git commit -m "feat: add trigger word matching for consent, opt-out, rejoin"
```

---

### Task 4: Message templates

**Files:**
- Create: `tests/consent/test_messages.py`
- Create: `app/consent/messages.py`

- [ ] **Step 1: Write the failing test**

Create `tests/consent/test_messages.py`:
```python
from app.consent.messages import get_message


def test_unknown_message_is_french():
    msg = get_message("unknown", "en")
    # Unknown always returns French regardless of language param
    assert "réservé aux participants" in msg


def test_consent_prompt_fr():
    msg = get_message("consent_prompt", "fr")
    assert "Répondez OUI" in msg


def test_consent_prompt_en():
    msg = get_message("consent_prompt", "en")
    assert "Reply YES" in msg


def test_consent_prompt_es():
    msg = get_message("consent_prompt", "es")
    assert "Responda SÍ" in msg


def test_consent_prompt_pt():
    msg = get_message("consent_prompt", "pt")
    assert "Responda SIM" in msg


def test_opted_out_fr():
    msg = get_message("opted_out", "fr")
    assert "désabonné" in msg


def test_opted_out_en():
    msg = get_message("opted_out", "en")
    assert "unsubscribed" in msg


def test_welcome_back_fr():
    msg = get_message("welcome_back", "fr")
    assert "Bon retour" in msg


def test_welcome_back_en():
    msg = get_message("welcome_back", "en")
    assert "Welcome back" in msg


def test_unknown_language_falls_back_to_fr():
    msg = get_message("consent_prompt", "xx")
    assert "Répondez OUI" in msg
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/consent/test_messages.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'app.consent.messages'`

- [ ] **Step 3: Write minimal implementation**

Create `app/consent/messages.py`:
```python
REGISTRATION_LINK = "https://chomei.store/register"

MESSAGES = {
    "unknown": {
        "fr": (
            "Ce service est réservé aux participants inscrits à "
            f"#BuildingResilience. Pour vous inscrire : {REGISTRATION_LINK}"
        ),
    },
    "consent_prompt": {
        "fr": (
            "Bienvenue à #BuildingResilience ! Je suis votre assistant IA pour "
            "l'événement. Pour continuer, j'ai besoin de votre consentement. "
            "Vos messages seront traités par une intelligence artificielle et "
            "vos données seront anonymisées conformément au RGPD. "
            "Répondez OUI pour accepter."
        ),
        "en": (
            "Welcome to #BuildingResilience! I'm your AI assistant for the "
            "event. To continue, I need your consent. Your messages will be "
            "processed by artificial intelligence and your data will be "
            "anonymised in compliance with GDPR. Reply YES to accept."
        ),
        "es": (
            "Bienvenido/a a #BuildingResilience. Soy su asistente IA para el "
            "evento. Para continuar, necesito su consentimiento. Sus mensajes "
            "serán procesados por inteligencia artificial y sus datos serán "
            "anonimizados conforme al RGPD. Responda SÍ para aceptar."
        ),
        "pt": (
            "Bem-vindo/a ao #BuildingResilience! Sou o seu assistente IA para "
            "o evento. Para continuar, preciso do seu consentimento. As suas "
            "mensagens serão processadas por inteligência artificial e os seus "
            "dados serão anonimizados em conformidade com o RGPD. "
            "Responda SIM para aceitar."
        ),
    },
    "opted_out": {
        "fr": (
            "Vous vous êtes désabonné(e). Vos données anonymisées sont "
            "conservées. Pour vous réinscrire, envoyez REJOINDRE."
        ),
        "en": (
            "You have unsubscribed. Your anonymised data is retained. "
            "To re-subscribe, send JOIN."
        ),
        "es": (
            "Se ha dado de baja. Sus datos anonimizados se conservan. "
            "Para volver a suscribirse, envíe UNIRSE."
        ),
        "pt": (
            "Cancelou a subscrição. Os seus dados anonimizados são "
            "conservados. Para se reinscrever, envie JUNTAR."
        ),
    },
    "welcome_back": {
        "fr": (
            "Bon retour ! Votre accès à l'assistant #BuildingResilience "
            "est réactivé. Comment puis-je vous aider ?"
        ),
        "en": (
            "Welcome back! Your access to the #BuildingResilience assistant "
            "has been reactivated. How can I help you?"
        ),
        "es": (
            "Bienvenido/a de nuevo. Su acceso al asistente "
            "#BuildingResilience ha sido reactivado. ¿En qué puedo ayudarle?"
        ),
        "pt": (
            "Bem-vindo/a de volta! O seu acesso ao assistente "
            "#BuildingResilience foi reativado. Como posso ajudá-lo/a?"
        ),
    },
}


def get_message(message_type: str, language: str) -> str:
    """Get a localised message. Falls back to French if language not found."""
    templates = MESSAGES[message_type]
    if message_type == "unknown":
        return templates["fr"]
    return templates.get(language, templates["fr"])
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/consent/test_messages.py -v
```
Expected: 11 passed.

- [ ] **Step 5: Commit**

```bash
git add app/consent/messages.py tests/consent/test_messages.py
git commit -m "feat: add multilingual message templates (FR/EN/ES/PT)"
```

---

### Task 5: Supabase client initialisation

**Files:**
- Create: `app/supabase_client.py`

- [ ] **Step 1: Create the Supabase client module**

Create `app/supabase_client.py`:
```python
from supabase import create_client, Client
from decouple import config


def get_supabase() -> Client:
    """Create and return a Supabase client."""
    return create_client(
        config("SUPABASE_URL"),
        config("SUPABASE_KEY"),
    )
```

- [ ] **Step 2: Commit**

```bash
git add app/supabase_client.py
git commit -m "feat: add Supabase client initialisation"
```

---

### Task 6: Consent state machine

**Files:**
- Create: `tests/consent/test_state_machine.py`
- Create: `app/consent/state_machine.py`

- [ ] **Step 1: Write the failing test**

Create `tests/consent/test_state_machine.py`:
```python
from unittest.mock import MagicMock
from app.consent.state_machine import resolve_consent_state, process_message


def _mock_supabase(row=None):
    """Create a mock Supabase client that returns the given row."""
    sb = MagicMock()
    query = sb.table.return_value.select.return_value.eq.return_value.execute
    if row:
        query.return_value.data = [row]
    else:
        query.return_value.data = []
    return sb


def test_resolve_unknown_when_no_row():
    sb = _mock_supabase(row=None)
    state = resolve_consent_state(sb, "somehash")
    assert state is None


def test_resolve_registered():
    sb = _mock_supabase(row={"consent_status": "registered", "language": "fr"})
    state = resolve_consent_state(sb, "somehash")
    assert state["consent_status"] == "registered"
    assert state["language"] == "fr"


def test_resolve_active():
    sb = _mock_supabase(row={"consent_status": "active", "language": "en"})
    state = resolve_consent_state(sb, "somehash")
    assert state["consent_status"] == "active"


def test_process_unknown_sender():
    sb = _mock_supabase(row=None)
    result = process_message(sb, "+447700900000", "hello")
    assert result["action"] == "reject"
    assert "réservé" in result["reply"]


def test_process_registered_with_consent_keyword():
    sb = _mock_supabase(row={"consent_status": "registered", "language": "en"})
    # Mock the update call
    sb.table.return_value.update.return_value.eq.return_value.execute.return_value = None
    result = process_message(sb, "+447700900000", "YES")
    assert result["action"] == "activate"
    sb.table.return_value.update.assert_called()


def test_process_registered_without_consent_keyword():
    sb = _mock_supabase(row={"consent_status": "registered", "language": "fr"})
    result = process_message(sb, "+447700900000", "bonjour")
    assert result["action"] == "prompt_consent"
    assert "Répondez OUI" in result["reply"]


def test_process_active_normal_message():
    sb = _mock_supabase(row={"consent_status": "active", "language": "en"})
    result = process_message(sb, "+447700900000", "What is the event schedule?")
    assert result["action"] == "forward_to_ai"


def test_process_active_opt_out():
    sb = _mock_supabase(row={"consent_status": "active", "language": "en"})
    sb.table.return_value.update.return_value.eq.return_value.execute.return_value = None
    result = process_message(sb, "+447700900000", "STOP")
    assert result["action"] == "opt_out"
    assert "unsubscribed" in result["reply"]
    sb.table.return_value.update.assert_called()


def test_process_opted_out_rejoin():
    sb = _mock_supabase(row={"consent_status": "opted_out", "language": "fr"})
    sb.table.return_value.update.return_value.eq.return_value.execute.return_value = None
    result = process_message(sb, "+447700900000", "REJOINDRE")
    assert result["action"] == "rejoin"
    assert "Bon retour" in result["reply"]
    sb.table.return_value.update.assert_called()


def test_process_opted_out_no_rejoin():
    sb = _mock_supabase(row={"consent_status": "opted_out", "language": "en"})
    result = process_message(sb, "+447700900000", "hello")
    assert result["action"] == "remind_opted_out"
    assert "unsubscribed" in result["reply"]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/consent/test_state_machine.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'app.consent.state_machine'`

- [ ] **Step 3: Write minimal implementation**

Create `app/consent/state_machine.py`:
```python
from datetime import datetime, timezone

from supabase import Client

from app.consent.hashing import hash_phone_number
from app.consent.triggers import match_trigger
from app.consent.messages import get_message

REGISTRATION_TABLE = "registrations"


def resolve_consent_state(supabase: Client, phone_hash: str) -> dict | None:
    """Look up a phone hash in the registration table. Returns row dict or None."""
    result = (
        supabase.table(REGISTRATION_TABLE)
        .select("consent_status, language")
        .eq("phone_hash", phone_hash)
        .execute()
    )
    if result.data:
        return result.data[0]
    return None


def _update_consent(supabase: Client, phone_hash: str, updates: dict) -> None:
    """Update consent fields on the registration table."""
    supabase.table(REGISTRATION_TABLE).update(updates).eq(
        "phone_hash", phone_hash
    ).execute()


def process_message(supabase: Client, phone: str, body: str) -> dict:
    """
    Process an incoming WhatsApp message through the consent state machine.

    Returns a dict with:
        action: str — what happened (reject, prompt_consent, activate, forward_to_ai, opt_out, rejoin, remind_opted_out)
        reply: str | None — message to send back (None if forward_to_ai)
    """
    phone_hash = hash_phone_number(phone)
    state = resolve_consent_state(supabase, phone_hash)
    trigger = match_trigger(body)

    # Unknown sender
    if state is None:
        return {"action": "reject", "reply": get_message("unknown", "fr")}

    status = state["consent_status"]
    lang = state.get("language", "fr")

    # Registered — awaiting consent
    if status == "registered":
        if trigger == "consent":
            now = datetime.now(timezone.utc).isoformat()
            _update_consent(supabase, phone_hash, {
                "consent_status": "active",
                "consent_given_at": now,
            })
            return {"action": "activate", "reply": None}
        return {"action": "prompt_consent", "reply": get_message("consent_prompt", lang)}

    # Active
    if status == "active":
        if trigger == "opt_out":
            now = datetime.now(timezone.utc).isoformat()
            _update_consent(supabase, phone_hash, {
                "consent_status": "opted_out",
                "consent_revoked_at": now,
            })
            return {"action": "opt_out", "reply": get_message("opted_out", lang)}
        return {"action": "forward_to_ai", "reply": None}

    # Opted out
    if status == "opted_out":
        if trigger == "rejoin":
            now = datetime.now(timezone.utc).isoformat()
            _update_consent(supabase, phone_hash, {
                "consent_status": "active",
                "consent_given_at": now,
                "consent_revoked_at": None,
            })
            return {"action": "rejoin", "reply": get_message("welcome_back", lang)}
        return {"action": "remind_opted_out", "reply": get_message("opted_out", lang)}

    return {"action": "reject", "reply": get_message("unknown", "fr")}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/consent/test_state_machine.py -v
```
Expected: 10 passed.

- [ ] **Step 5: Commit**

```bash
git add app/consent/state_machine.py tests/consent/test_state_machine.py
git commit -m "feat: add consent state machine with Supabase lookups"
```

---

### Task 7: Refactor main.py webhook to use consent state machine

**Files:**
- Modify: `main.py`
- Create: `tests/consent/test_integration.py`

- [ ] **Step 1: Write the failing integration test**

Create `tests/consent/test_integration.py`:
```python
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient


def _mock_supabase_with_state(state_row):
    """Return a mock Supabase client that returns state_row on lookup."""
    sb = MagicMock()
    query = sb.table.return_value.select.return_value.eq.return_value.execute
    if state_row:
        query.return_value.data = [state_row]
    else:
        query.return_value.data = []
    sb.table.return_value.update.return_value.eq.return_value.execute.return_value = None
    return sb


@patch("main.get_supabase")
def test_unknown_sender_gets_rejection(mock_get_sb):
    mock_get_sb.return_value = _mock_supabase_with_state(None)
    from main import app
    client = TestClient(app)
    response = client.post("/message", data={"From": "whatsapp:+440000000000", "Body": "hello"})
    assert response.status_code == 200
    assert "réservé" in response.text


@patch("main.get_supabase")
def test_registered_sender_gets_consent_prompt(mock_get_sb):
    mock_get_sb.return_value = _mock_supabase_with_state(
        {"consent_status": "registered", "language": "en"}
    )
    from main import app
    client = TestClient(app)
    response = client.post("/message", data={"From": "whatsapp:+441111111111", "Body": "hi"})
    assert response.status_code == 200
    assert "Reply YES" in response.text


@patch("main.get_supabase")
@patch("main.run_ai_query")
def test_active_sender_gets_ai_response(mock_ai, mock_get_sb):
    mock_get_sb.return_value = _mock_supabase_with_state(
        {"consent_status": "active", "language": "en"}
    )
    mock_ai.return_value = "The event starts at 9am."
    from main import app
    client = TestClient(app)
    response = client.post("/message", data={"From": "whatsapp:+442222222222", "Body": "When does it start?"})
    assert response.status_code == 200
    assert "9am" in response.text


@patch("main.get_supabase")
def test_active_sender_opts_out(mock_get_sb):
    mock_get_sb.return_value = _mock_supabase_with_state(
        {"consent_status": "active", "language": "fr"}
    )
    from main import app
    client = TestClient(app)
    response = client.post("/message", data={"From": "whatsapp:+443333333333", "Body": "STOP"})
    assert response.status_code == 200
    assert "désabonné" in response.text
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/consent/test_integration.py -v
```
Expected: FAIL — imports and functions don't exist yet in refactored main.py.

- [ ] **Step 3: Refactor main.py**

Replace the full contents of `main.py` with:
```python
from fastapi import FastAPI, Form, Request
from fastapi.responses import PlainTextResponse
from twilio.twiml.messaging_response import MessagingResponse
from decouple import config

from app.supabase_client import get_supabase
from app.consent.state_machine import process_message

import logging

logger = logging.getLogger(__name__)

# Twilio config
account_sid = config("TWILIO_ACCOUNT_SID")
auth_token = config("TWILIO_AUTH_TOKEN")
twilio_number = config("TWILIO_NUMBER")

app = FastAPI()


def run_ai_query(message: str) -> str:
    """Placeholder for Claude AI integration (WA-B04). Returns AI response."""
    # TODO: Replace with Claude API call in WA-B04 implementation
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
        # User just consented — send a confirmation and handle their first message
        response_text = run_ai_query(Body) if Body.strip().lower() not in {
            "yes", "oui", "si", "sí", "sim"
        } else get_message_for_activation(result, phone, supabase)
    else:
        response_text = result["reply"]

    # Build Twilio XML response
    twilio_response = MessagingResponse()
    twilio_response.message(response_text)
    xml = str(twilio_response)
    logger.info(f"Response to {phone[:6]}***: {result['action']}")
    return PlainTextResponse(xml, media_type="application/xml")


def get_message_for_activation(result, phone, supabase):
    """After consent, send consent_prompt success in their language."""
    from app.consent.hashing import hash_phone_number
    from app.consent.state_machine import resolve_consent_state
    state = resolve_consent_state(supabase, hash_phone_number(phone))
    lang = state.get("language", "fr") if state else "fr"
    from app.consent.messages import get_message
    return get_message("welcome_back", lang)


@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 4: Run integration tests**

```bash
pytest tests/consent/test_integration.py -v
```
Expected: 4 passed.

- [ ] **Step 5: Run all tests**

```bash
pytest -v
```
Expected: All tests pass (hashing: 4, triggers: 18, messages: 11, state_machine: 10, integration: 4 = 47 total).

- [ ] **Step 6: Commit**

```bash
git add main.py tests/consent/test_integration.py
git commit -m "feat: refactor webhook to use consent state machine, add health endpoint"
```

---

### Task 8: Add Supabase schema migration SQL

**Files:**
- Create: `db/migrations/001_add_consent_columns.sql`

- [ ] **Step 1: Create migration directory**

```bash
mkdir -p db/migrations
```

- [ ] **Step 2: Write migration SQL**

Create `db/migrations/001_add_consent_columns.sql`:
```sql
-- Add consent tracking columns to the registration table.
-- Run this in the Supabase SQL Editor.

ALTER TABLE registrations
ADD COLUMN IF NOT EXISTS consent_status text NOT NULL DEFAULT 'registered'
    CHECK (consent_status IN ('registered', 'active', 'opted_out'));

ALTER TABLE registrations
ADD COLUMN IF NOT EXISTS consent_given_at timestamptz;

ALTER TABLE registrations
ADD COLUMN IF NOT EXISTS consent_revoked_at timestamptz;

-- Add phone_hash column if it doesn't already exist.
-- If your registration table already stores phone hashes, skip this.
ALTER TABLE registrations
ADD COLUMN IF NOT EXISTS phone_hash text;

-- Index for fast webhook lookups
CREATE INDEX IF NOT EXISTS idx_registrations_phone_hash
ON registrations (phone_hash);

-- Backfill phone_hash for existing rows (if raw phone numbers exist).
-- Replace 'phone_number' with the actual column name holding raw numbers.
-- Run this ONCE then remove raw phone numbers for RGPD compliance.
--
-- UPDATE registrations
-- SET phone_hash = encode(sha256(phone_number::bytea), 'hex')
-- WHERE phone_hash IS NULL AND phone_number IS NOT NULL;
```

- [ ] **Step 3: Commit**

```bash
git add db/migrations/001_add_consent_columns.sql
git commit -m "feat: add Supabase migration for consent columns"
```

---

### Task 9: Update .env.example and CLAUDE.md

**Files:**
- Create: `.env.example`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Create .env.example**

Create `.env.example`:
```bash
# Twilio
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_NUMBER=

# Supabase
SUPABASE_URL=
SUPABASE_KEY=

# Anthropic (for WA-B04)
ANTHROPIC_API_KEY=
```

- [ ] **Step 2: Update CLAUDE.md environment variables section**

In `CLAUDE.md`, update the Environment Variables section to reflect the current state:

Replace the **Target (new architecture)** line with:
```
**Active:** `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_NUMBER`, `SUPABASE_URL`, `SUPABASE_KEY`. See `.env.example`.
```

- [ ] **Step 3: Run all tests one final time**

```bash
pytest -v
```
Expected: All 47 tests pass.

- [ ] **Step 4: Commit**

```bash
git add .env.example CLAUDE.md
git commit -m "docs: add .env.example, update CLAUDE.md for new architecture"
```

---

## Summary

| Task | What it builds | Tests |
|------|---------------|-------|
| 1 | Project structure, dependencies | — |
| 2 | Phone hashing | 4 |
| 3 | Trigger word matching | 18 |
| 4 | Message templates (4 langs) | 11 |
| 5 | Supabase client | — |
| 6 | Consent state machine | 10 |
| 7 | Webhook refactor + integration | 4 |
| 8 | DB migration SQL | — |
| 9 | Config and docs | — |
| **Total** | | **47** |
