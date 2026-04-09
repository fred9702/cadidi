# Design Spec: KB Integration, Post-Opt-In Menu & Human Escalation

**Date:** 2026-04-09
**Status:** Approved

## Overview

Three interconnected features for the Cadidi WhatsApp assistant:

1. **KB Integration** — Inject campaign knowledge base content into Claude's system prompt at startup
2. **Post-Opt-In Menu** — Show a topic selection menu after consent activation to guide the user's first interaction
3. **Human Escalation** — Allow Claude to escalate conversations to a human operator, with endpoints for human response and resolution

## 1. KB Integration + System Prompt

### KB Loading

At module load time, `app/ai/system_prompt.py` reads three markdown files from the project root and embeds their content into the system prompt's `--- KNOWLEDGE BASE ---` section:

- `PROGRAMME_KB.md` — Event programme / schedule
- `CAP241_KB.md` — CAP 241 framework and its four pillars
- `BuildingResilience_KB.md` — Campaign overview, OAFLAD, Fondation Ma Banniere, EQUILIBRES programme

Files are read once at import time (static embed). Server restart required to pick up KB changes. This is acceptable for a single-day event with stable content.

### System Prompt Changes

- **Fix OAFLAD name:** Change from "Organisation Africaine des Femmes Leaders pour l'Agriculture et le Developpement" to "Organisation des Premieres Dames d'Afrique pour le Developpement" (FR) / "Organization of African First Ladies for Development" (EN)
- **Add escalation instruction:** Tell Claude to prepend `[ESCALATE]` to its response when a human should handle the conversation. Include examples: VIP logistics requests, complaints, medical emergencies, anything Claude cannot confidently answer from the KB
- **Add escalation reason instruction:** After the `[ESCALATE]` marker, Claude should include a brief reason tag `[REASON: ...]` before its user-facing response, so the backend can extract and log the reason
- **Add scope guidance:** Claude should answer questions using KB content, not invent details. If information is not in the KB, say so and offer to escalate

### System Prompt Structure

```
You are the official AI assistant for #BuildingResilience...

Event details: ...

{language_instruction}

Tone and style: ...

Scope: ...

Escalation rules:
- When you determine a human should handle this conversation, prepend [ESCALATE][REASON: brief reason] to your response
- Examples of when to escalate: ...
- Your response after the tags should be a natural message to the user acknowledging the handoff

--- KNOWLEDGE BASE ---
{kb_content}
--- END KNOWLEDGE BASE ---
```

## 2. Post-Opt-In Menu

### New Message: `welcome_menu`

Add a `"welcome_menu"` message type to `app/consent/messages.py` (bilingual FR/EN). Displayed immediately after consent activation or reactivation. This is a static message, not sent to Claude.

**French:**
```
Bienvenue ! Je suis votre assistant IA pour #BuildingResilience.

Comment puis-je vous aider ? Par exemple :
1. La campagne #BuildingResilience
2. Le cadre CAP 241
3. La Fondation Ma Banniere
4. Le programme de l'evenement
5. L'OAFLAD/OPDAD

Vous pouvez aussi poser n'importe quelle question librement.
```

**English:**
```
Welcome! I'm your AI assistant for #BuildingResilience.

How can I help you? For example:
1. The #BuildingResilience campaign
2. The CAP 241 framework
3. The Ma Banniere Foundation
4. The event programme
5. OAFLAD/OPDAD

You can also ask any question freely.
```

### Flow Change in `main.py`

When `result["action"] == "activate"` (fresh consent) or `result["action"] == "rejoin"` (reactivation), send `welcome_menu` instead of the current `welcome_back` message. The menu appears once; subsequent messages go to Claude via `forward_to_ai`.

## 3. Human Escalation System

### Supabase Table: `wa_escalations`

```sql
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

### Escalation Detection: `app/escalation/detector.py`

After receiving Claude's response in `main.py`:

1. Check if response starts with `[ESCALATE]`
2. If yes: extract the `[REASON: ...]` tag and the user-facing message (everything after the tags)
3. Return a structured result: `{"escalated": True, "reason": "...", "reply": "..."}`
4. If no: return `{"escalated": False, "reason": None, "reply": original_response}`

### Escalation Manager: `app/escalation/manager.py`

Three functions:

- `create_escalation(supabase, conversation_id, phone_hash, reason, user_message)` — Insert into `wa_escalations` with status `open`
- `get_open_escalation(supabase, phone_hash)` — Return the open escalation row for a phone_hash, or None
- `resolve_escalation(supabase, phone_hash)` — Set status to `resolved`, set `resolved_at`

### Escalated User Handling in `main.py`

In the `forward_to_ai` branch, before calling Claude:

1. Check `get_open_escalation(phone_hash)`
2. If open escalation exists: save the user's message to `wa_messages`, respond with a holding message ("Your request is being handled by the team. / Votre demande est prise en charge par l'equipe."), skip Claude API call
3. If no open escalation: proceed normally with Claude

After calling Claude (when no open escalation):

1. Parse response through `detector.parse_response()`
2. If escalated: call `create_escalation()`, save the cleaned reply to `wa_messages`, send cleaned reply to user
3. If not escalated: save response to `wa_messages`, send to user (existing flow)

### Human Response Endpoint: `POST /respond`

Located in `app/escalation/router.py`. Authenticated with same Bearer token as `/broadcast` (reuses `app/broadcast/auth.py`).

**Request body:**
```json
{
    "phone": "+241XXXXXXXX",
    "message": "Response from the organising team..."
}
```

**Behavior:**
1. Validate auth (Bearer token)
2. Validate payload (phone and message required)
3. Hash the phone number
4. Look up active conversation for the phone_hash
5. If no active conversation: return 404 (the user must have an active conversation to receive a response)
6. Save message to `wa_messages` with `role: "assistant"` (so Claude sees it in history as continuity)
7. Send via `send_whatsapp(phone, message)`
8. Return `{"status": "sent"}`

Note: `/respond` does not require an open escalation. A human operator can proactively message any user with an active conversation. This is intentional — it allows operators to follow up even after resolving an escalation.

### Resolve Endpoint: `POST /resolve`

Located in same router. Authenticated identically.

**Request body:**
```json
{
    "phone": "+241XXXXXXXX"
}
```

**Behavior:**
1. Validate auth
2. Hash the phone number
3. Call `resolve_escalation(supabase, phone_hash)`
4. If no open escalation found: return 404
5. Return `{"status": "resolved"}`

After resolution, the user's next message goes back to Claude normally.

## File Changes

### New Files
- `app/escalation/__init__.py`
- `app/escalation/detector.py` — Parse `[ESCALATE][REASON: ...]` from Claude response
- `app/escalation/manager.py` — CRUD for wa_escalations table
- `app/escalation/router.py` — `/respond` and `/resolve` endpoints
- `supabase/migrations/<timestamp>_create_wa_escalations.sql`

### Modified Files
- `app/ai/system_prompt.py` — Load KB files at startup, fix OAFLAD name, add escalation + scope instructions
- `app/consent/messages.py` — Add `welcome_menu` message type
- `main.py` — Send menu on activate/rejoin, check open escalation before Claude, detect escalation in response, register escalation router

### Unchanged Files
- `app/ai/client.py`
- `app/ai/history.py`
- `app/ai/conversations.py`
- `app/broadcast/auth.py` (reused, not modified)
- `app/broadcast/router.py`

## Holding Messages

Add to `app/consent/messages.py` as a new message type `"escalation_holding"`:

- **FR:** "Votre demande est prise en charge par l'equipe organisatrice. Vous recevrez une reponse prochainement dans cette conversation."
- **EN:** "Your request is being handled by the organising team. You'll receive a response shortly in this conversation."
