# Claude API Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the AI placeholder with Claude API integration, add conversation session management, and message persistence.

**Architecture:** New `app/ai/` package with four modules (system_prompt, conversations, history, client). Two Supabase migrations create `wa_conversations` and `wa_messages` tables. Consent state machine updated to return language. Main.py wired to the new AI modules.

**Tech Stack:** anthropic SDK, Supabase, FastAPI, python-decouple

---

## File Map

| Action | File | Responsibility |
|---|---|---|
| Create | `supabase/migrations/20260402120000_create_wa_conversations.sql` | wa_conversations table |
| Create | `supabase/migrations/20260402120001_create_wa_messages.sql` | wa_messages table |
| Create | `app/ai/__init__.py` | Package init |
| Create | `app/ai/system_prompt.py` | System prompt constant |
| Create | `app/ai/conversations.py` | Session management |
| Create | `app/ai/history.py` | Message persistence |
| Create | `app/ai/client.py` | Claude API wrapper |
| Modify | `app/consent/state_machine.py:93` | Return language in forward_to_ai |
| Modify | `main.py:26-50` | Replace placeholder with AI flow |
| Modify | `requirements.txt` | Add anthropic |
| Modify | `.env.example` | Add ANTHROPIC_API_KEY |
| Modify | `tests/conftest.py` | Add ANTHROPIC_API_KEY dummy |
| Create | `tests/ai/__init__.py` | Test package |
| Create | `tests/ai/test_system_prompt.py` | System prompt tests |
| Create | `tests/ai/test_conversations.py` | Conversation session tests |
| Create | `tests/ai/test_history.py` | Message history tests |
| Create | `tests/ai/test_client.py` | Claude client tests |
| Modify | `tests/consent/test_state_machine.py` | Update forward_to_ai assertion |

---

### Task 1: Database Migrations

**Files:**
- Create: `supabase/migrations/20260402120000_create_wa_conversations.sql`
- Create: `supabase/migrations/20260402120001_create_wa_messages.sql`

- [ ] **Step 1: Create wa_conversations migration**

```sql
-- Create conversation session table for multi-turn WhatsApp AI interactions.

CREATE TABLE wa_conversations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    phone_hash text NOT NULL,
    started_at timestamptz NOT NULL DEFAULT now(),
    last_message_at timestamptz NOT NULL DEFAULT now(),
    status text NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'expired')),
    language text NOT NULL DEFAULT 'fr'
);

CREATE INDEX idx_wa_conversations_phone_hash
ON wa_conversations (phone_hash);

CREATE INDEX idx_wa_conversations_active_lookup
ON wa_conversations (phone_hash, status);
```

- [ ] **Step 2: Create wa_messages migration**

```sql
-- Create message log table for conversation history.

CREATE TABLE wa_messages (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id uuid NOT NULL REFERENCES wa_conversations(id),
    role text NOT NULL CHECK (role IN ('user', 'assistant')),
    content text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_wa_messages_conversation_id
ON wa_messages (conversation_id);
```

- [ ] **Step 3: Apply migrations to Supabase**

Run:
```bash
supabase db push
```

- [ ] **Step 4: Commit**

```bash
git add supabase/migrations/20260402120000_create_wa_conversations.sql supabase/migrations/20260402120001_create_wa_messages.sql
git commit -m "feat: add wa_conversations and wa_messages migrations"
```

---

### Task 2: System Prompt Module

**Files:**
- Create: `tests/ai/__init__.py`
- Create: `tests/ai/test_system_prompt.py`
- Create: `app/ai/__init__.py`
- Create: `app/ai/system_prompt.py`

- [ ] **Step 1: Create test package and write failing test**

Create `tests/ai/__init__.py` (empty) and `tests/ai/test_system_prompt.py`:

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


def test_system_prompt_contains_knowledge_base_placeholder():
    prompt = get_system_prompt("fr")
    assert "KNOWLEDGE BASE" in prompt.upper() or "knowledge base" in prompt.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/ai/test_system_prompt.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Create app/ai package and implement system_prompt.py**

Create `app/ai/__init__.py` (empty) and `app/ai/system_prompt.py`:

```python
LANGUAGE_INSTRUCTIONS = {
    "fr": "Réponds toujours en français.",
    "en": "Always respond in English.",
}

SYSTEM_PROMPT_TEMPLATE = """\
You are the official AI assistant for #BuildingResilience, a high-level Pan-African \
conference organised by OAFLAD (Organisation Africaine des Femmes Leaders pour \
l'Agriculture et le Développement).

Event details:
- Date: 17 April 2026
- Location: Libreville, Gabon
- Expected attendance: approximately 1,000 participants
- Theme: Building Resilience — strengthening African communities

{language_instruction}

Tone and style:
- Professional, warm, and helpful
- Appropriate for a prestigious Pan-African conference
- Keep responses concise and WhatsApp-friendly (short paragraphs, no markdown)
- Use plain text with line breaks, no bullet points or formatting symbols

Scope:
- Answer questions about the #BuildingResilience event
- For topics outside your scope, politely redirect the user to the event organisers

--- KNOWLEDGE BASE ---
Content will be provided here as it becomes available. For now, use only the event \
details above.
--- END KNOWLEDGE BASE ---\
"""


def get_system_prompt(language: str) -> str:
    """Return the system prompt with language-specific instruction."""
    lang_instruction = LANGUAGE_INSTRUCTIONS.get(
        language, LANGUAGE_INSTRUCTIONS["fr"]
    )
    return SYSTEM_PROMPT_TEMPLATE.format(language_instruction=lang_instruction)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/ai/test_system_prompt.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add app/ai/__init__.py app/ai/system_prompt.py tests/ai/__init__.py tests/ai/test_system_prompt.py
git commit -m "feat: add system prompt module for Claude AI assistant"
```

---

### Task 3: Conversation Session Management

**Files:**
- Create: `tests/ai/test_conversations.py`
- Create: `app/ai/conversations.py`

- [ ] **Step 1: Write failing tests**

Create `tests/ai/test_conversations.py`:

```python
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta

from app.ai.conversations import get_or_create_conversation, SESSION_EXPIRY_HOURS

CONVERSATIONS_TABLE = "wa_conversations"


def _mock_supabase(select_rows=None, insert_row=None):
    """Mock Supabase client for conversation queries."""
    sb = MagicMock()
    table_mock = sb.table.return_value

    # SELECT chain: .select().eq().eq().execute()
    select_chain = table_mock.select.return_value.eq.return_value.eq.return_value
    select_chain.execute.return_value.data = select_rows or []

    # INSERT chain: .insert().execute()
    if insert_row:
        table_mock.insert.return_value.execute.return_value.data = [insert_row]
    else:
        table_mock.insert.return_value.execute.return_value.data = [
            {"id": "new-conv-id", "phone_hash": "abc", "language": "fr",
             "status": "active", "last_message_at": datetime.now(timezone.utc).isoformat()}
        ]

    # UPDATE chain: .update().eq().execute()
    table_mock.update.return_value.eq.return_value.execute.return_value = None

    return sb


def test_creates_new_conversation_when_none_exists():
    sb = _mock_supabase(select_rows=[])
    conv = get_or_create_conversation(sb, "hash123", "fr")
    assert conv["id"] == "new-conv-id"
    sb.table.return_value.insert.assert_called_once()


def test_returns_existing_active_conversation():
    now = datetime.now(timezone.utc)
    existing = {
        "id": "existing-id",
        "phone_hash": "hash123",
        "language": "fr",
        "status": "active",
        "last_message_at": now.isoformat(),
    }
    sb = _mock_supabase(select_rows=[existing])
    conv = get_or_create_conversation(sb, "hash123", "fr")
    assert conv["id"] == "existing-id"
    # Should update last_message_at
    sb.table.return_value.update.assert_called()


def test_expires_stale_conversation_and_creates_new():
    stale_time = (datetime.now(timezone.utc) - timedelta(hours=SESSION_EXPIRY_HOURS + 1)).isoformat()
    stale = {
        "id": "stale-id",
        "phone_hash": "hash123",
        "language": "fr",
        "status": "active",
        "last_message_at": stale_time,
    }
    sb = _mock_supabase(select_rows=[stale])
    conv = get_or_create_conversation(sb, "hash123", "fr")
    # Should have called update twice: once to expire, once for new conversation's last_message_at
    # And insert once for the new conversation
    sb.table.return_value.insert.assert_called_once()


def test_session_expiry_hours_is_24():
    assert SESSION_EXPIRY_HOURS == 24
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/ai/test_conversations.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Implement conversations.py**

Create `app/ai/conversations.py`:

```python
from datetime import datetime, timezone, timedelta

from supabase import Client

SESSION_EXPIRY_HOURS = 24
CONVERSATIONS_TABLE = "wa_conversations"


def get_or_create_conversation(supabase: Client, phone_hash: str, language: str) -> dict:
    """Get an active conversation or create a new one.

    Expires conversations older than SESSION_EXPIRY_HOURS.
    """
    result = (
        supabase.table(CONVERSATIONS_TABLE)
        .select("*")
        .eq("phone_hash", phone_hash)
        .eq("status", "active")
        .execute()
    )

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=SESSION_EXPIRY_HOURS)

    if result.data:
        conv = result.data[0]
        last_msg = datetime.fromisoformat(conv["last_message_at"])
        if last_msg > cutoff:
            # Active and fresh — update timestamp
            supabase.table(CONVERSATIONS_TABLE).update(
                {"last_message_at": now.isoformat()}
            ).eq("id", conv["id"]).execute()
            return conv
        # Stale — expire it
        supabase.table(CONVERSATIONS_TABLE).update(
            {"status": "expired"}
        ).eq("id", conv["id"]).execute()

    # Create new conversation
    new_conv = (
        supabase.table(CONVERSATIONS_TABLE)
        .insert({
            "phone_hash": phone_hash,
            "language": language,
            "status": "active",
            "started_at": now.isoformat(),
            "last_message_at": now.isoformat(),
        })
        .execute()
    )
    return new_conv.data[0]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/ai/test_conversations.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add app/ai/conversations.py tests/ai/test_conversations.py
git commit -m "feat: add conversation session management with 24h expiry"
```

---

### Task 4: Message History Module

**Files:**
- Create: `tests/ai/test_history.py`
- Create: `app/ai/history.py`

- [ ] **Step 1: Write failing tests**

Create `tests/ai/test_history.py`:

```python
from unittest.mock import MagicMock

from app.ai.history import save_message, load_history, DEFAULT_HISTORY_LIMIT

MESSAGES_TABLE = "wa_messages"


def test_save_message_inserts_row():
    sb = MagicMock()
    sb.table.return_value.insert.return_value.execute.return_value = None
    save_message(sb, "conv-123", "user", "Hello")
    sb.table.return_value.insert.assert_called_once_with({
        "conversation_id": "conv-123",
        "role": "user",
        "content": "Hello",
    })


def test_load_history_returns_formatted_messages():
    sb = MagicMock()
    rows = [
        {"role": "user", "content": "Hi", "created_at": "2026-04-02T10:00:00"},
        {"role": "assistant", "content": "Hello!", "created_at": "2026-04-02T10:00:01"},
    ]
    sb.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = rows
    history = load_history(sb, "conv-123")
    assert history == [
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello!"},
    ]


def test_load_history_empty_conversation():
    sb = MagicMock()
    sb.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []
    history = load_history(sb, "conv-123")
    assert history == []


def test_default_history_limit_is_20():
    assert DEFAULT_HISTORY_LIMIT == 20
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/ai/test_history.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Implement history.py**

Create `app/ai/history.py`:

```python
from supabase import Client

DEFAULT_HISTORY_LIMIT = 20
MESSAGES_TABLE = "wa_messages"


def save_message(supabase: Client, conversation_id: str, role: str, content: str) -> None:
    """Insert a message into wa_messages."""
    supabase.table(MESSAGES_TABLE).insert({
        "conversation_id": conversation_id,
        "role": role,
        "content": content,
    }).execute()


def load_history(supabase: Client, conversation_id: str, limit: int = DEFAULT_HISTORY_LIMIT) -> list[dict]:
    """Load recent messages for a conversation, formatted for Claude Messages API."""
    result = (
        supabase.table(MESSAGES_TABLE)
        .select("role, content")
        .eq("conversation_id", conversation_id)
        .order("created_at", desc=False)
        .limit(limit)
        .execute()
    )
    return [{"role": row["role"], "content": row["content"]} for row in result.data]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/ai/test_history.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add app/ai/history.py tests/ai/test_history.py
git commit -m "feat: add message history persistence for multi-turn conversations"
```

---

### Task 5: Claude API Client

**Files:**
- Create: `tests/ai/test_client.py`
- Create: `app/ai/client.py`
- Modify: `requirements.txt`
- Modify: `.env.example`
- Modify: `tests/conftest.py`

- [ ] **Step 1: Add anthropic dependency**

Add `anthropic` to `requirements.txt` (after `httpx`):

```
anthropic
```

Then install:
```bash
source .venv/bin/activate && pip install anthropic
```

- [ ] **Step 2: Add ANTHROPIC_API_KEY to .env.example and conftest**

In `.env.example`, ensure this line exists:
```
ANTHROPIC_API_KEY=
```

In `tests/conftest.py`, add:
```python
os.environ.setdefault("ANTHROPIC_API_KEY", "test_anthropic_key")
```

- [ ] **Step 3: Write failing tests**

Create `tests/ai/test_client.py`:

```python
from unittest.mock import patch, MagicMock

from app.ai.client import get_ai_response, MODEL, ERROR_MESSAGES


def _mock_claude_response(text):
    """Create a mock Anthropic Messages response."""
    response = MagicMock()
    block = MagicMock()
    block.text = text
    response.content = [block]
    return response


@patch("app.ai.client.anthropic.Anthropic")
def test_get_ai_response_returns_text(mock_anthropic_cls):
    mock_client = mock_anthropic_cls.return_value
    mock_client.messages.create.return_value = _mock_claude_response("Bonjour!")
    history = [{"role": "user", "content": "Salut"}]
    result = get_ai_response(history, "fr")
    assert result == "Bonjour!"
    mock_client.messages.create.assert_called_once()


@patch("app.ai.client.anthropic.Anthropic")
def test_get_ai_response_passes_correct_model(mock_anthropic_cls):
    mock_client = mock_anthropic_cls.return_value
    mock_client.messages.create.return_value = _mock_claude_response("Hi!")
    get_ai_response([{"role": "user", "content": "Hi"}], "en")
    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == MODEL


@patch("app.ai.client.anthropic.Anthropic")
def test_get_ai_response_passes_history_as_messages(mock_anthropic_cls):
    mock_client = mock_anthropic_cls.return_value
    mock_client.messages.create.return_value = _mock_claude_response("Reply")
    history = [
        {"role": "user", "content": "First"},
        {"role": "assistant", "content": "Response"},
        {"role": "user", "content": "Second"},
    ]
    get_ai_response(history, "fr")
    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["messages"] == history


@patch("app.ai.client.anthropic.Anthropic")
def test_get_ai_response_returns_error_message_on_failure(mock_anthropic_cls):
    mock_client = mock_anthropic_cls.return_value
    mock_client.messages.create.side_effect = Exception("API error")
    result = get_ai_response([{"role": "user", "content": "Hi"}], "fr")
    assert result == ERROR_MESSAGES["fr"]


@patch("app.ai.client.anthropic.Anthropic")
def test_get_ai_response_error_message_in_english(mock_anthropic_cls):
    mock_client = mock_anthropic_cls.return_value
    mock_client.messages.create.side_effect = Exception("API error")
    result = get_ai_response([{"role": "user", "content": "Hi"}], "en")
    assert result == ERROR_MESSAGES["en"]
```

- [ ] **Step 4: Run test to verify it fails**

Run: `pytest tests/ai/test_client.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 5: Implement client.py**

Create `app/ai/client.py`:

```python
import logging

import anthropic
from decouple import config

from app.ai.system_prompt import get_system_prompt

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 1024

ERROR_MESSAGES = {
    "fr": "Je rencontre un problème technique. Veuillez réessayer dans un instant.",
    "en": "I'm having a technical issue. Please try again shortly.",
}


def get_ai_response(history: list[dict], language: str) -> str:
    """Call Claude API with conversation history and return the response text."""
    try:
        client = anthropic.Anthropic(api_key=config("ANTHROPIC_API_KEY"))
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=get_system_prompt(language),
            messages=history,
        )
        return response.content[0].text
    except Exception:
        logger.exception("Claude API call failed")
        return ERROR_MESSAGES.get(language, ERROR_MESSAGES["fr"])
```

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/ai/test_client.py -v`
Expected: All 5 tests PASS

- [ ] **Step 7: Commit**

```bash
git add app/ai/client.py tests/ai/test_client.py requirements.txt .env.example tests/conftest.py
git commit -m "feat: add Claude API client with error handling"
```

---

### Task 6: Update Consent State Machine

**Files:**
- Modify: `app/consent/state_machine.py:93`
- Modify: `tests/consent/test_state_machine.py`

- [ ] **Step 1: Update existing test to expect language in forward_to_ai**

In `tests/consent/test_state_machine.py`, update `test_process_active_normal_message`:

```python
def test_process_active_normal_message():
    sb = _mock_supabase(row={"consent_status": "active", "language_pref": "en"})
    result = process_message(sb, "+447700900000", "What is the event schedule?")
    assert result["action"] == "forward_to_ai"
    assert result["language"] == "en"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/consent/test_state_machine.py::test_process_active_normal_message -v`
Expected: FAIL with KeyError: 'language'

- [ ] **Step 3: Update state machine to return language**

In `app/consent/state_machine.py`, change line 93 from:

```python
        return {"action": "forward_to_ai", "reply": None}
```

to:

```python
        return {"action": "forward_to_ai", "reply": None, "language": lang}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/consent/test_state_machine.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add app/consent/state_machine.py tests/consent/test_state_machine.py
git commit -m "feat: return language in forward_to_ai consent result"
```

---

### Task 7: Wire Everything Into main.py

**Files:**
- Modify: `main.py:1-61`

- [ ] **Step 1: Replace placeholder with full AI flow**

Update `main.py` to:

```python
from fastapi import FastAPI, Form, Request
from fastapi.responses import Response
from twilio.rest import Client
from decouple import config

from app.supabase_client import get_supabase
from app.consent.state_machine import process_message
from app.consent.messages import get_message
from app.consent.hashing import hash_phone_number
from app.consent.state_machine import resolve_consent_state
from app.ai.conversations import get_or_create_conversation
from app.ai.history import save_message, load_history
from app.ai.client import get_ai_response

import logging

logger = logging.getLogger(__name__)

# Twilio config
account_sid = config("TWILIO_ACCOUNT_SID")
auth_token = config("TWILIO_AUTH_TOKEN")
twilio_number = config("TWILIO_WHATSAPP_NUMBER")
messaging_service_sid = config("TWILIO_MESSAGING_SERVICE_SID")
twilio_client = Client(account_sid, auth_token)

app = FastAPI()


def send_whatsapp(to: str, body: str) -> None:
    """Send a WhatsApp message via Twilio Messaging Service."""
    twilio_client.messages.create(
        messaging_service_sid=messaging_service_sid,
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

- [ ] **Step 2: Run full test suite**

Run: `pytest -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "feat: wire Claude API integration into webhook handler"
```

---

### Task 8: Run Full Test Suite and Verify

- [ ] **Step 1: Run all tests**

Run: `pytest -v`
Expected: All tests across `tests/consent/` and `tests/ai/` PASS

- [ ] **Step 2: Start dev server and verify health endpoint**

Run: `source .venv/bin/activate && uvicorn main:app --reload`
Then in another terminal: `curl http://localhost:8000/health`
Expected: `{"status":"ok"}`

- [ ] **Step 3: Verify no import errors**

Run: `python -c "from app.ai.client import get_ai_response; from app.ai.conversations import get_or_create_conversation; from app.ai.history import save_message, load_history; print('All imports OK')"`
Expected: `All imports OK`
