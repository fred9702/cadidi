# Design Spec: Claude-Powered Operator Agent CLI

**Date:** 2026-04-09
**Status:** Approved

## Overview

An interactive CLI tool that helps human operators manage escalated WhatsApp conversations. It lists open escalations, shows conversation context, uses Claude to draft responses, and lets the operator approve/edit/reject before sending. Lives inside the cadidi repo at `tools/operator.py`.

## Architecture

Three external services:
- **Supabase** (direct read) — fetch open escalations and conversation history
- **Cadidi API** (`POST /respond`, `POST /resolve`) — send messages and close escalations
- **Claude API** — draft operator responses

## Interactive Loop

```
1. Fetch open escalations from wa_escalations (joined with registrations for phone)
2. Display list: index, timestamp, reason, user message preview
3. Operator picks one by number (or 'q' to quit, 'r' to refresh)
4. Fetch conversation history from wa_messages for that conversation_id
5. Display conversation context (role + content for each message)
6. Send context + escalation reason to Claude API to draft a response
7. Display Claude's draft
8. Operator chooses:
   - [a]pprove — send as-is via POST /respond
   - [e]dit — operator edits the draft in terminal, then send
   - [r]eject — Claude generates a new draft (back to step 7)
   - [s]kip — back to step 1 without acting
9. After sending: prompt "Resolve this escalation? [y/n]"
   - y → POST /resolve
   - n → leave open (operator may want to send more messages)
10. Loop back to step 1
```

## Claude Draft Response

**Model:** `claude-sonnet-4-6` (fast, cost-effective for short drafts)

**System prompt:**
```
You are an assistant helping a human operator respond to escalated WhatsApp 
conversations from the #BuildingResilience conference (17 April 2026, Libreville, 
Gabon). 

Draft a response to send to the user. Rules:
- Write in the same language as the user's messages
- Be professional, warm, and helpful
- Keep it concise and WhatsApp-friendly (plain text, no markdown)
- Address their specific request or concern
- If you don't have enough context to answer, say so and suggest the operator 
  add details before sending
```

**User message sent to Claude:**
```
Escalation reason: {reason}

Conversation history:
{formatted history — role: content for each message}

Draft a response to the user's latest message.
```

**Max tokens:** 512 (WhatsApp messages should be short)

## Data Flow

### Fetching Escalations

```sql
SELECT e.id, e.conversation_id, e.phone_hash, e.reason, e.user_message, 
       e.created_at, r.phone, c.language
FROM wa_escalations e
JOIN registrations r ON r.phone_hash = e.phone_hash
JOIN wa_conversations c ON c.id = e.conversation_id
WHERE e.status = 'open'
ORDER BY e.created_at ASC
```

In practice, this is done via Supabase client chained queries since Supabase JS/Python client doesn't support raw SQL joins. The tool will:
1. Fetch open escalations from `wa_escalations`
2. For each, look up the phone from `registrations` by `phone_hash`
3. For each, look up the language from `wa_conversations` by `conversation_id`

### Fetching Conversation History

```python
supabase.table("wa_messages")
    .select("role, content, created_at")
    .eq("conversation_id", conversation_id)
    .order("created_at")
    .execute()
```

### Sending Response

```
POST {CADIDI_API_URL}/respond
Authorization: Bearer {BROADCAST_API_KEY}
{"phone": "+241...", "message": "..."}
```

### Resolving Escalation

```
POST {CADIDI_API_URL}/resolve
Authorization: Bearer {BROADCAST_API_KEY}
{"phone": "+241..."}
```

## Configuration

All from existing `.env` via `decouple.config`:
- `SUPABASE_URL` — Supabase project URL
- `SUPABASE_KEY` — Supabase service key
- `ANTHROPIC_API_KEY` — Claude API key
- `BROADCAST_API_KEY` — auth token for /respond and /resolve

New optional env var:
- `CADIDI_API_URL` — base URL for cadidi API, defaults to `http://localhost:8000`

## File Structure

### New Files
- `tools/operator.py` — the entire CLI tool

### No Modified Files

## Functions

| Function | Purpose |
|----------|---------|
| `fetch_open_escalations(supabase)` | Query wa_escalations (open), enrich with phone from registrations and language from wa_conversations |
| `fetch_conversation_history(supabase, conversation_id)` | Query wa_messages ordered by created_at |
| `draft_response(client, history, reason, language)` | Call Claude API to draft a response |
| `send_response(api_url, api_key, phone, message)` | POST /respond |
| `resolve_escalation(api_url, api_key, phone)` | POST /resolve |
| `display_escalations(escalations)` | Format and print the escalation list |
| `display_conversation(messages)` | Format and print conversation history |
| `main()` | Interactive loop |

## Dependencies

No new pip dependencies. Uses:
- `anthropic` — Claude API client (already in requirements.txt)
- `supabase` — Supabase client (already in requirements.txt)
- `python-decouple` — env var loading (already in requirements.txt)
- `httpx` — HTTP calls to cadidi API (already in requirements.txt)

## Error Handling

- Supabase query failures: print error, continue loop
- `/respond` or `/resolve` HTTP errors: print status + detail, don't crash
- Claude API errors: print error, offer to skip or retry
- Empty escalation list: print "No open escalations" and wait for 'r' to refresh or 'q' to quit
- Network errors: catch and display, don't crash the loop

## Usage

```bash
cd /home/chomei/bomalab/cadidi
source .venv/bin/activate
python tools/operator.py
```
