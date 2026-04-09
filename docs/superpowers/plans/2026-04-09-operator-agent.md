# Operator Agent CLI — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an interactive CLI tool that helps operators manage escalated WhatsApp conversations using Claude to draft responses.

**Architecture:** Single Python script at `tools/operator.py`. Reads escalations and conversation history directly from Supabase, uses Claude API to draft responses, sends via cadidi's `/respond` and `/resolve` HTTP endpoints. Interactive loop with approve/edit/reject/skip workflow.

**Tech Stack:** Python 3, anthropic SDK, supabase-py, httpx, python-decouple

**Spec:** `docs/superpowers/specs/2026-04-09-operator-agent-design.md`

---

## File Structure

### New Files
| File | Responsibility |
|------|---------------|
| `tools/operator.py` | Interactive CLI tool — all functions and main loop |
| `tests/tools/__init__.py` | Test package init |
| `tests/tools/test_operator.py` | Tests for operator tool functions |

---

## Task 1: Supabase Read Functions

**Files:**
- Create: `tools/operator.py`
- Create: `tests/tools/__init__.py`
- Create: `tests/tools/test_operator.py`

- [ ] **Step 1: Write failing tests for fetch functions**

File: `tests/tools/test_operator.py`

```python
import sys
import os

# Add project root to path so tools/ is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from unittest.mock import MagicMock
from tools.operator import fetch_open_escalations, fetch_conversation_history


def _mock_supabase():
    return MagicMock()


def test_fetch_open_escalations_returns_enriched_list():
    sb = _mock_supabase()

    # wa_escalations query
    esc_result = MagicMock()
    esc_result.data = [
        {
            "id": "esc-1",
            "conversation_id": "conv-1",
            "phone_hash": "hash-abc",
            "reason": "VIP request",
            "user_message": "I need help",
            "created_at": "2026-04-17T10:00:00Z",
        }
    ]

    # registrations query
    reg_result = MagicMock()
    reg_result.data = [{"phone": "+241060000001"}]

    # wa_conversations query
    conv_result = MagicMock()
    conv_result.data = [{"language": "fr"}]

    # Chain mocks: each .table() call returns a fresh chain
    call_count = {"n": 0}
    original_table = sb.table

    def table_router(name):
        chain = MagicMock()
        if name == "wa_escalations":
            chain.select.return_value.eq.return_value.order.return_value.execute.return_value = esc_result
        elif name == "registrations":
            chain.select.return_value.eq.return_value.execute.return_value = reg_result
        elif name == "wa_conversations":
            chain.select.return_value.eq.return_value.execute.return_value = conv_result
        return chain

    sb.table = table_router

    result = fetch_open_escalations(sb)
    assert len(result) == 1
    assert result[0]["phone"] == "+241060000001"
    assert result[0]["language"] == "fr"
    assert result[0]["reason"] == "VIP request"


def test_fetch_open_escalations_returns_empty_list():
    sb = _mock_supabase()
    esc_result = MagicMock()
    esc_result.data = []

    def table_router(name):
        chain = MagicMock()
        if name == "wa_escalations":
            chain.select.return_value.eq.return_value.order.return_value.execute.return_value = esc_result
        return chain

    sb.table = table_router

    result = fetch_open_escalations(sb)
    assert result == []


def test_fetch_conversation_history():
    sb = _mock_supabase()
    msg_result = MagicMock()
    msg_result.data = [
        {"role": "user", "content": "Hello", "created_at": "2026-04-17T10:00:00Z"},
        {"role": "assistant", "content": "Hi there", "created_at": "2026-04-17T10:00:05Z"},
    ]
    sb.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = msg_result

    result = fetch_conversation_history(sb, "conv-1")
    assert len(result) == 2
    assert result[0]["role"] == "user"
    assert result[1]["role"] == "assistant"
```

- [ ] **Step 2: Create test package init and run tests to verify they fail**

Create empty `tests/tools/__init__.py`.

Run: `pytest tests/tools/test_operator.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.operator'`

- [ ] **Step 3: Implement fetch functions**

Create `tools/operator.py`:

```python
"""Operator agent CLI — manage escalated WhatsApp conversations with Claude-assisted drafts."""

from supabase import Client


def fetch_open_escalations(supabase: Client) -> list[dict]:
    """Fetch open escalations enriched with phone number and language."""
    esc_result = (
        supabase.table("wa_escalations")
        .select("id, conversation_id, phone_hash, reason, user_message, created_at")
        .eq("status", "open")
        .order("created_at")
        .execute()
    )

    if not esc_result.data:
        return []

    enriched = []
    for esc in esc_result.data:
        # Look up real phone from registrations
        reg = (
            supabase.table("registrations")
            .select("phone")
            .eq("phone_hash", esc["phone_hash"])
            .execute()
        )
        phone = reg.data[0]["phone"] if reg.data else None

        # Look up language from conversation
        conv = (
            supabase.table("wa_conversations")
            .select("language")
            .eq("id", esc["conversation_id"])
            .execute()
        )
        language = conv.data[0]["language"] if conv.data else "fr"

        enriched.append({
            **esc,
            "phone": phone,
            "language": language,
        })

    return enriched


def fetch_conversation_history(supabase: Client, conversation_id: str) -> list[dict]:
    """Fetch message history for a conversation, ordered by time."""
    result = (
        supabase.table("wa_messages")
        .select("role, content, created_at")
        .eq("conversation_id", conversation_id)
        .order("created_at")
        .execute()
    )
    return result.data
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/tools/test_operator.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add tools/operator.py tests/tools/__init__.py tests/tools/test_operator.py
git commit -m "feat(operator): add Supabase read functions for escalations and history"
```

---

## Task 2: Claude Draft Response Function

**Files:**
- Modify: `tools/operator.py`
- Modify: `tests/tools/test_operator.py`

- [ ] **Step 1: Write failing test for draft_response**

Append to `tests/tools/test_operator.py`:

```python
from unittest.mock import patch, MagicMock
from tools.operator import draft_response


def test_draft_response_calls_claude():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(type="text", text="Bonjour, je vais vous aider.")]
    mock_client.messages.create.return_value = mock_response

    history = [
        {"role": "user", "content": "J'ai besoin d'aide", "created_at": "2026-04-17T10:00:00Z"},
    ]

    result = draft_response(mock_client, history, "VIP logistics", "fr")
    assert result == "Bonjour, je vais vous aider."

    call_kwargs = mock_client.messages.create.call_args[1]
    assert call_kwargs["model"] == "claude-sonnet-4-6"
    assert call_kwargs["max_tokens"] == 512
    assert "VIP logistics" in call_kwargs["messages"][0]["content"]


def test_draft_response_includes_history():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(type="text", text="Response")]
    mock_client.messages.create.return_value = mock_response

    history = [
        {"role": "user", "content": "Hello", "created_at": "2026-04-17T10:00:00Z"},
        {"role": "assistant", "content": "Hi", "created_at": "2026-04-17T10:00:05Z"},
        {"role": "user", "content": "Help me", "created_at": "2026-04-17T10:00:10Z"},
    ]

    draft_response(mock_client, history, "General help", "en")

    call_kwargs = mock_client.messages.create.call_args[1]
    user_msg = call_kwargs["messages"][0]["content"]
    assert "Hello" in user_msg
    assert "Hi" in user_msg
    assert "Help me" in user_msg
```

- [ ] **Step 2: Run tests to verify new tests fail**

Run: `pytest tests/tools/test_operator.py::test_draft_response_calls_claude -v`
Expected: FAIL — `ImportError: cannot import name 'draft_response'`

- [ ] **Step 3: Implement draft_response**

Add to `tools/operator.py`:

```python
import anthropic

DRAFT_MODEL = "claude-sonnet-4-6"
DRAFT_MAX_TOKENS = 512

DRAFT_SYSTEM_PROMPT = """\
You are an assistant helping a human operator respond to escalated WhatsApp \
conversations from the #BuildingResilience conference (17 April 2026, Libreville, \
Gabon).

Draft a response to send to the user. Rules:
- Write in the same language as the user's messages
- Be professional, warm, and helpful
- Keep it concise and WhatsApp-friendly (plain text, no markdown)
- Address their specific request or concern
- If you don't have enough context to answer, say so and suggest the operator \
add details before sending\
"""


def draft_response(
    client: anthropic.Anthropic,
    history: list[dict],
    reason: str,
    language: str,
) -> str:
    """Use Claude to draft a response for the operator."""
    formatted_history = "\n".join(
        f"{msg['role']}: {msg['content']}" for msg in history
    )

    user_message = (
        f"Escalation reason: {reason}\n\n"
        f"Conversation history:\n{formatted_history}\n\n"
        f"Draft a response to the user's latest message."
    )

    response = client.messages.create(
        model=DRAFT_MODEL,
        max_tokens=DRAFT_MAX_TOKENS,
        system=DRAFT_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    return next(
        (block.text for block in response.content if block.type == "text"), ""
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/tools/test_operator.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add tools/operator.py tests/tools/test_operator.py
git commit -m "feat(operator): add Claude-powered draft_response function"
```

---

## Task 3: HTTP Client Functions (send_response, resolve_escalation)

**Files:**
- Modify: `tools/operator.py`
- Modify: `tests/tools/test_operator.py`

- [ ] **Step 1: Write failing tests for HTTP functions**

Append to `tests/tools/test_operator.py`:

```python
import httpx
from tools.operator import send_response, resolve_escalation


def test_send_response_posts_to_respond(httpx_mock):
    """Note: requires pytest-httpx. If not available, use unittest.mock."""
    pass  # See step 3 for mock-based approach


def test_send_response_success():
    with patch("tools.operator.httpx.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status": "sent"}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        success, detail = send_response(
            "http://localhost:8000", "test-key", "+241060000001", "Hello"
        )
        assert success is True
        assert detail == {"status": "sent"}

        mock_post.assert_called_once_with(
            "http://localhost:8000/respond",
            json={"phone": "+241060000001", "message": "Hello"},
            headers={"Authorization": "Bearer test-key"},
            timeout=30,
        )


def test_send_response_failure():
    with patch("tools.operator.httpx.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.json.return_value = {"detail": "No active conversation"}
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404", request=MagicMock(), response=mock_resp
        )
        mock_post.return_value = mock_resp

        success, detail = send_response(
            "http://localhost:8000", "test-key", "+241060000001", "Hello"
        )
        assert success is False


def test_resolve_escalation_success():
    with patch("tools.operator.httpx.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status": "resolved"}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        success, detail = resolve_escalation(
            "http://localhost:8000", "test-key", "+241060000001"
        )
        assert success is True
        assert detail == {"status": "resolved"}


def test_resolve_escalation_failure():
    with patch("tools.operator.httpx.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.json.return_value = {"detail": "No open escalation"}
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404", request=MagicMock(), response=mock_resp
        )
        mock_post.return_value = mock_resp

        success, detail = resolve_escalation(
            "http://localhost:8000", "test-key", "+241060000001"
        )
        assert success is False
```

- [ ] **Step 2: Run tests to verify new tests fail**

Run: `pytest tests/tools/test_operator.py::test_send_response_success -v`
Expected: FAIL — `ImportError: cannot import name 'send_response'`

- [ ] **Step 3: Implement HTTP functions**

Add to `tools/operator.py`:

```python
import httpx


def send_response(
    api_url: str, api_key: str, phone: str, message: str
) -> tuple[bool, dict]:
    """Send a human response via POST /respond. Returns (success, response_json)."""
    try:
        resp = httpx.post(
            f"{api_url}/respond",
            json={"phone": phone, "message": message},
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30,
        )
        resp.raise_for_status()
        return True, resp.json()
    except httpx.HTTPStatusError as e:
        return False, e.response.json() if e.response else {"detail": str(e)}
    except httpx.RequestError as e:
        return False, {"detail": f"Connection error: {e}"}


def resolve_escalation(
    api_url: str, api_key: str, phone: str
) -> tuple[bool, dict]:
    """Resolve an escalation via POST /resolve. Returns (success, response_json)."""
    try:
        resp = httpx.post(
            f"{api_url}/resolve",
            json={"phone": phone},
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30,
        )
        resp.raise_for_status()
        return True, resp.json()
    except httpx.HTTPStatusError as e:
        return False, e.response.json() if e.response else {"detail": str(e)}
    except httpx.RequestError as e:
        return False, {"detail": f"Connection error: {e}"}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/tools/test_operator.py -v`
Expected: All 9 tests PASS (3 fetch + 2 draft + 4 HTTP)

- [ ] **Step 5: Commit**

```bash
git add tools/operator.py tests/tools/test_operator.py
git commit -m "feat(operator): add HTTP client functions for /respond and /resolve"
```

---

## Task 4: Display Functions and Interactive Main Loop

**Files:**
- Modify: `tools/operator.py`

- [ ] **Step 1: Add display functions**

Add to `tools/operator.py`:

```python
def display_escalations(escalations: list[dict]) -> None:
    """Print a numbered list of open escalations."""
    print("\n=== Open Escalations ===\n")
    for i, esc in enumerate(escalations, 1):
        ts = esc["created_at"][:16].replace("T", " ")
        reason = esc.get("reason", "No reason given")
        preview = esc["user_message"][:60]
        phone = esc.get("phone", "unknown")
        print(f"  [{i}] {ts}  |  {reason}")
        print(f"      Phone: {phone}")
        print(f"      Message: {preview}...")
        print()


def display_conversation(messages: list[dict]) -> None:
    """Print conversation history."""
    print("\n--- Conversation History ---\n")
    for msg in messages:
        role_label = "USER" if msg["role"] == "user" else "ASSISTANT"
        ts = msg.get("created_at", "")[:16].replace("T", " ")
        print(f"  [{role_label}] {ts}")
        print(f"  {msg['content']}")
        print()
```

- [ ] **Step 2: Add the main interactive loop**

Add to `tools/operator.py`:

```python
from decouple import config


def main():
    """Interactive operator loop."""
    from app.supabase_client import get_supabase

    supabase = get_supabase()
    claude = anthropic.Anthropic(api_key=config("ANTHROPIC_API_KEY"))
    api_url = config("CADIDI_API_URL", default="http://localhost:8000")
    api_key = config("BROADCAST_API_KEY")

    print("=== #BuildingResilience Operator Agent ===")
    print("Manage escalated conversations with Claude-assisted drafts.\n")

    while True:
        escalations = fetch_open_escalations(supabase)

        if not escalations:
            print("No open escalations.")
            cmd = input("\n[r]efresh / [q]uit: ").strip().lower()
            if cmd == "q":
                break
            continue

        display_escalations(escalations)
        cmd = input(f"Pick [1-{len(escalations)}] / [r]efresh / [q]uit: ").strip().lower()

        if cmd == "q":
            break
        if cmd == "r":
            continue
        if not cmd.isdigit() or int(cmd) < 1 or int(cmd) > len(escalations):
            print("Invalid selection.")
            continue

        esc = escalations[int(cmd) - 1]

        if not esc.get("phone"):
            print("Error: no phone number found for this escalation.")
            continue

        # Show conversation context
        history = fetch_conversation_history(supabase, esc["conversation_id"])
        display_conversation(history)
        print(f"Escalation reason: {esc.get('reason', 'No reason given')}")
        print(f"Triggering message: {esc['user_message']}\n")

        # Draft loop
        while True:
            print("Generating draft response...")
            draft = draft_response(
                claude, history, esc.get("reason", ""), esc.get("language", "fr")
            )
            print(f"\n--- Draft ---\n{draft}\n--- End Draft ---\n")

            action = input("[a]pprove / [e]dit / [r]eject (new draft) / [s]kip: ").strip().lower()

            if action == "s":
                break

            if action == "r":
                continue  # Generate new draft

            if action == "e":
                print("Enter your edited response (end with an empty line):")
                lines = []
                while True:
                    line = input()
                    if line == "":
                        break
                    lines.append(line)
                draft = "\n".join(lines)
                if not draft.strip():
                    print("Empty response, skipping.")
                    continue

            if action in ("a", "e"):
                # Send the response
                print(f"\nSending to {esc['phone']}...")
                success, detail = send_response(api_url, api_key, esc["phone"], draft)
                if success:
                    print("Sent successfully.")
                else:
                    print(f"Failed to send: {detail}")
                    break

                # Ask about resolving
                resolve = input("\nResolve this escalation? [y/n]: ").strip().lower()
                if resolve == "y":
                    success, detail = resolve_escalation(api_url, api_key, esc["phone"])
                    if success:
                        print("Escalation resolved.")
                    else:
                        print(f"Failed to resolve: {detail}")
                break

        print()  # Blank line before next loop


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Run existing tests to make sure nothing broke**

Run: `pytest tests/tools/test_operator.py -v`
Expected: All 9 tests still PASS

- [ ] **Step 4: Manual smoke test**

Run: `python tools/operator.py`

If no escalations exist, you should see:
```
=== #BuildingResilience Operator Agent ===
Manage escalated conversations with Claude-assisted drafts.

No open escalations.

[r]efresh / [q]uit:
```

Press `q` to exit.

- [ ] **Step 5: Commit**

```bash
git add tools/operator.py
git commit -m "feat(operator): add display functions and interactive main loop"
```
