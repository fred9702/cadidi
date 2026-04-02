# Claude API Integration Design

**Date:** 2026-04-02
**Component:** WA-B04 (Backend — Claude Integration)
**Status:** Approved

## Overview

Replace the `run_ai_query()` placeholder in `main.py` with a full Claude API integration. The assistant serves registered, consented #BuildingResilience participants via WhatsApp with multi-turn conversation support, session management, and bilingual responses.

## Database Schema

### `wa_conversations`

Groups messages into sessions per user. A conversation expires after 24 hours of inactivity.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | uuid | PK, default `gen_random_uuid()` | |
| `phone_hash` | text | NOT NULL, indexed | Links to registrations.phone_hash |
| `started_at` | timestamptz | NOT NULL, default `now()` | Session start |
| `last_message_at` | timestamptz | NOT NULL, default `now()` | Updated on each message |
| `status` | text | NOT NULL, default `'active'`, CHECK `IN ('active', 'expired')` | |
| `language` | text | NOT NULL, default `'fr'` | From registrations.language_pref |

Indexes: `phone_hash`, `(phone_hash, status)` for active session lookup.

### `wa_messages`

Individual messages within a conversation.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | uuid | PK, default `gen_random_uuid()` | |
| `conversation_id` | uuid | NOT NULL, FK → wa_conversations(id) | |
| `role` | text | NOT NULL, CHECK `IN ('user', 'assistant')` | |
| `content` | text | NOT NULL | Message body |
| `created_at` | timestamptz | NOT NULL, default `now()` | |

Index: `conversation_id`.

### Session Expiry

A conversation is considered expired when `last_message_at` is older than 24 hours. On each incoming message:
1. Query for an active conversation where `last_message_at` > (now - 24h)
2. If found, update `last_message_at` and continue
3. If not found (or existing is stale), mark old conversation as `expired`, create a new one

## Module Structure

```
app/ai/
├── __init__.py
├── client.py          # Claude API calls
├── system_prompt.py   # System prompt constant
├── history.py         # Load/save messages (wa_messages)
└── conversations.py   # Session management (wa_conversations)
```

### `app/ai/conversations.py`

**`get_or_create_conversation(supabase, phone_hash, language) -> dict`**

1. Query `wa_conversations` for rows matching `phone_hash` with `status = 'active'`
2. If found and `last_message_at` is within 24 hours: update `last_message_at` to now, return the row
3. If found but stale: update `status` to `'expired'`, then create new
4. If not found: create new conversation with `status = 'active'`
5. Returns the conversation dict (id, phone_hash, language, etc.)

### `app/ai/history.py`

**`save_message(supabase, conversation_id, role, content) -> None`**

Insert a row into `wa_messages`.

**`load_history(supabase, conversation_id, limit=20) -> list[dict]`**

Query `wa_messages` for the conversation, ordered by `created_at` ascending, limited to the most recent `limit` messages. Returns list of `{"role": "user"|"assistant", "content": "..."}` — the format Claude's Messages API expects.

### `app/ai/client.py`

**`get_ai_response(history, language) -> str`**

1. Build system prompt from `system_prompt.py`, injecting the user's language
2. Call `anthropic.Anthropic().messages.create()` with:
   - `model`: `claude-sonnet-4-6` (fast, cost-effective for high-volume WhatsApp)
   - `max_tokens`: 1024 (WhatsApp messages should be concise)
   - `system`: the system prompt
   - `messages`: the conversation history
3. Extract and return the text response

The `ANTHROPIC_API_KEY` is read via `decouple.config("ANTHROPIC_API_KEY")`.

### `app/ai/system_prompt.py`

**`get_system_prompt(language) -> str`**

Returns the system prompt with language instruction. The prompt defines:

- **Identity:** AI assistant for #BuildingResilience, a Pan-African conference by OAFLAD
- **Event details:** 17 April 2026, Libreville, Gabon, ~1,000 participants
- **Language:** Respond in the user's preferred language (FR or EN). Handle PT natively.
- **Tone:** Professional, warm, helpful. Appropriate for a high-level Pan-African conference.
- **Scope:** Answer questions about the event. For topics outside scope, politely redirect.
- **Knowledge base placeholder:** A clearly marked section where campaign content (speakers, programme, FAQ) will be injected later.
- **Constraints:** Keep responses concise (WhatsApp-friendly). No markdown formatting (WhatsApp doesn't render it well). Use plain text with line breaks.

## Request Flow (updated)

```
Twilio webhook
  → POST /message (main.py)
  → consent state machine (process_message)
  → if action == "forward_to_ai":
      → get_or_create_conversation(supabase, phone_hash, lang)
      → save_message(conversation_id, "user", body)
      → load_history(conversation_id)
      → get_ai_response(history, lang)
      → save_message(conversation_id, "assistant", response)
      → send_whatsapp(phone, response)
```

## main.py Changes

- Remove `run_ai_query()` placeholder
- Import from `app.ai` modules
- In the `forward_to_ai` branch: resolve language from consent state, run the flow above
- The `activate` branch remains unchanged (returns `welcome_back` message)

## Consent State Machine Change

`process_message()` currently returns `{"action": "forward_to_ai", "reply": None}` but does not include the user's language. Update it to also return `"language": lang` so `main.py` can pass it to the AI modules without an extra Supabase lookup.

## Configuration

- `ANTHROPIC_API_KEY` — already set on Railway, added to `.env.example`
- Model constant in `client.py`: `MODEL = "claude-sonnet-4-6"`
- Session expiry constant in `conversations.py`: `SESSION_EXPIRY_HOURS = 24`
- History limit constant in `history.py`: `DEFAULT_HISTORY_LIMIT = 20`

## Dependencies

Add `anthropic` to `requirements.txt`.

## Error Handling

- If the Claude API call fails, return a polite error message in the user's language ("I'm having trouble right now, please try again shortly")
- Log the error for debugging
- Don't expose API errors to the user

## RGPD Compliance

- No raw phone numbers stored in `wa_conversations` or `wa_messages` — only `phone_hash`
- Message content is stored (required for multi-turn) but linked only to hashed identifiers
- Session expiry provides natural data lifecycle
