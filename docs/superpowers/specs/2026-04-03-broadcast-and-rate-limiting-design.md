# Broadcast Endpoint & Per-User Rate Limiting Design

**Date:** 2026-04-03
**Components:** WA-B06 (Rate Limiting), WA-B08 (Broadcast Endpoint)
**Status:** Approved

## Overview

Two independent features for the #BuildingResilience WhatsApp AI assistant:

1. **Broadcast endpoint** — An authenticated API endpoint that sends a WhatsApp message to all active (consented) participants, with optional language filtering for bilingual (FR/EN) announcements.
2. **Per-user rate limiting** — In-memory sliding window rate limiter that prevents individual users from spamming the Claude API, protecting against abuse and controlling costs.

---

## Feature 1: Broadcast Endpoint

### Purpose

Allow administrators to send announcements to all consented participants via a simple HTTP call. Use cases include event reminders, schedule changes, logistical updates, and post-event follow-ups.

### Authentication

The endpoint is protected by a bearer token (`BROADCAST_API_KEY` env var). Comparison uses `secrets.compare_digest` for timing-safe validation, preventing timing attacks.

- Missing or invalid token returns `401 Unauthorized`
- The key is stored as an environment variable on Railway alongside other secrets

### Endpoint

`POST /broadcast`

**Request headers:**
```
Authorization: Bearer <BROADCAST_API_KEY>
Content-Type: application/json
```

**Request body:**
```json
{
  "message": "Rappel : #BuildingResilience commence demain à 9h !",
  "language": "fr"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `message` | string | Yes | The message text to broadcast |
| `language` | string | No | Filter recipients by `language_pref` (e.g., `"fr"`, `"en"`). If omitted, sends to all active users. |

**Response (200):**
```json
{
  "sent": 423,
  "failed": 2
}
```

**Error responses:**
- `401` — Missing or invalid API key
- `400` — Missing `message` field in request body

### Recipient Resolution

1. Query `registrations` table for rows where:
   - `consent_status = 'active'`
   - `phone IS NOT NULL` (need raw phone number for Twilio)
   - If `language` param provided: `language_pref = <language>`
2. For each matching row, call `send_whatsapp(phone, message)` via the existing Twilio helper
3. Count successes and failures; log failures but don't abort the broadcast

### RGPD Note

The broadcast reads the raw `phone` column from `registrations` — this is the phone number provided during website registration. It is not stored or logged by the broadcast module; it is only used transiently to send the Twilio message. The `phone` column exists in `registrations` as part of the registration data; the `phone_hash` column is what the webhook flow uses for RGPD-compliant lookups.

### Module Structure

```
app/broadcast/
├── __init__.py
├── auth.py      # API key validation
└── router.py    # FastAPI router with POST /broadcast
```

**`app/broadcast/auth.py`**

`verify_api_key(api_key: str) -> bool`

- Reads `BROADCAST_API_KEY` from `decouple.config`
- Compares using `secrets.compare_digest` (timing-safe)
- Returns `True` if valid, `False` otherwise

**`app/broadcast/router.py`**

- Defines a FastAPI `APIRouter` with prefix `/broadcast`
- `POST /` handler:
  1. Extract `Authorization` header, validate via `verify_api_key`
  2. Parse JSON body, validate `message` field present
  3. Query Supabase `registrations` for active users (with optional language filter)
  4. Iterate results, call `send_whatsapp(phone, message)` for each
  5. Catch per-message Twilio errors (don't abort entire broadcast)
  6. Return `{"sent": N, "failed": M}`

### Shared Twilio Helper

The `send_whatsapp` function currently lives in `main.py`. To avoid a circular import (broadcast router importing from main), extract it to `app/twilio_client.py` — a shared module that both `main.py` and the broadcast router import from. This module holds the Twilio client initialisation and the `send_whatsapp` function.

### Integration in main.py

- Extract `send_whatsapp` and Twilio config to `app/twilio_client.py`
- Import `send_whatsapp` from `app.twilio_client` in both `main.py` and `app/broadcast/router.py`
- Import and register the broadcast router: `app.include_router(broadcast_router)`

### Configuration

- `BROADCAST_API_KEY` — new env var, must be set on Railway before use

---

## Feature 2: Per-User Rate Limiting

### Purpose

Prevent individual users from sending excessive messages that trigger Claude API calls. Protects against:
- Accidental message flooding (e.g., a user rapidly tapping send)
- Intentional abuse
- Runaway API costs from a single user

### Approach: In-Memory Sliding Window

A simple in-memory dictionary keyed by `phone_hash`, storing a list of message timestamps. On each incoming message:

1. Prune timestamps older than the time window
2. Check if the remaining count exceeds the limit
3. If under limit, record the new timestamp and allow
4. If over limit, reject with a polite rate-limit message

**Why in-memory (not database):**
- Rate limit state is inherently ephemeral — it's fine if it resets on deploy
- No database queries needed for the fast path
- Simpler implementation, no migration required
- With ~1,000 participants and 60-second windows, memory usage is negligible

### Limits

| Constant | Value | Description |
|---|---|---|
| `RATE_LIMIT_MAX_MESSAGES` | 10 | Maximum messages per window |
| `RATE_LIMIT_WINDOW_SECONDS` | 60 | Sliding window duration in seconds |

10 messages per minute is generous for normal conversation but blocks rapid-fire abuse.

### Module

`app/rate_limit.py` — single module (not a package; the feature is simple enough).

**`check_rate_limit(phone_hash: str) -> bool`**

- Maintains a module-level dict: `_message_log: dict[str, list[float]]`
- On each call:
  1. Get current time
  2. Prune entries older than `RATE_LIMIT_WINDOW_SECONDS`
  3. If `len(entries) >= RATE_LIMIT_MAX_MESSAGES`, return `False` (rate-limited)
  4. Append current timestamp, return `True` (allowed)

### Rate Limit Message

When a user is rate-limited, they receive a polite bilingual message:

- **FR:** "Vous envoyez des messages trop rapidement. Veuillez patienter un moment avant de réessayer."
- **EN:** "You're sending messages too quickly. Please wait a moment before trying again."

The message is selected based on the user's `language_pref` from the consent result.

### Integration in main.py

In the `forward_to_ai` branch, after consent passes but before calling Claude:

```
if result["action"] == "forward_to_ai":
    phone_hash = hash_phone_number(phone)
    if not check_rate_limit(phone_hash):
        response_text = rate_limit_message(result["language"])
    else:
        # existing AI flow...
```

### Scope

- Rate limiting applies **only** to the `forward_to_ai` action (AI queries)
- Consent messages (OUI, STOP, REJOINDRE, etc.) are **never** rate-limited — users must always be able to manage their consent
- Broadcast messages are not rate-limited (they're admin-initiated, not user-initiated)

---

## Dependencies

No new Python packages required. Both features use existing dependencies (FastAPI, Supabase, Twilio, python-decouple).

## Error Handling

### Broadcast
- Individual Twilio send failures are caught and counted; the broadcast continues for remaining recipients
- Failures are logged with the phone hash (not raw number) for debugging
- If zero recipients match the query, return `{"sent": 0, "failed": 0}` (not an error)

### Rate Limiting
- Rate limiting failures are silent from an error perspective — the user simply gets a polite message
- No logging needed for rate-limited requests (they're expected behaviour, not errors)
