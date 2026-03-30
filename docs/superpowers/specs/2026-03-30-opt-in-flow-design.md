# Opt-In Flow Design — #BuildingResilience WhatsApp Platform

## Overview

An explicit consent-based opt-in flow for the WhatsApp AI assistant. Participants register externally and receive a wa.me/ link via email. On first message, their phone number is verified against the registration database and explicit consent is captured before granting access to the AI assistant.

## Constraints

- WhatsApp Business API requires user-initiated first contact
- RGPD compliance: explicit consent required, phone numbers stored as SHA-256 hashes only
- Supported languages: FR, EN, ES, PT (language preference captured at registration)
- Default language for unknown users: French
- ~1,000 expected participants
- Single entry point: wa.me/ link sent via registration email
- Opt-in grants access to AI assistant only (broadcasts and Community handled separately)

## State Model

Every sender exists in one of 4 states:

| State | Meaning | Trigger to enter |
|-------|---------|------------------|
| `unknown` | Phone hash not in registration table | N/A — absence of registration |
| `registered` | In registration table, hasn't opted in | External registration completed |
| `active` | Opted in, consent confirmed | User replies with consent keyword |
| `opted_out` | Previously active, withdrew consent | User sends opt-out keyword |

### State Transitions

```
unknown → (external registration) → registered
registered → (consent keyword) → active
active → (opt-out keyword) → opted_out
opted_out → (re-opt-in keyword) → active
```

## Trigger Words

All matched case-insensitively.

| Action | EN | FR | ES | PT |
|--------|----|----|----|----|
| Consent | YES | OUI | SI, SÍ | SIM |
| Opt-out | STOP | ARRÊTER, ARRETER | PARAR | PARAR |
| Re-opt-in | JOIN | REJOINDRE | UNIRSE | JUNTAR |

If a `registered` user sends anything other than a consent keyword, re-send the consent prompt in their preferred language.

## Message Flow

### Unknown sender (not in registration table)

Sent in French only (language preference unavailable for unregistered users):

- **FR:** "Ce service est réservé aux participants inscrits à #BuildingResilience. Pour vous inscrire : [registration link]"

### Registered sender (awaiting consent)

Sent in the user's preferred language from the registration table.

- **FR:** "Bienvenue à #BuildingResilience ! Je suis votre assistant IA pour l'événement. Pour continuer, j'ai besoin de votre consentement. Vos messages seront traités par une intelligence artificielle et vos données seront anonymisées conformément au RGPD. Répondez OUI pour accepter."
- **EN:** "Welcome to #BuildingResilience! I'm your AI assistant for the event. To continue, I need your consent. Your messages will be processed by artificial intelligence and your data will be anonymised in compliance with GDPR. Reply YES to accept."
- **ES:** "Bienvenido/a a #BuildingResilience. Soy su asistente IA para el evento. Para continuar, necesito su consentimiento. Sus mensajes serán procesados por inteligencia artificial y sus datos serán anonimizados conforme al RGPD. Responda SÍ para aceptar."
- **PT:** "Bem-vindo/a ao #BuildingResilience! Sou o seu assistente IA para o evento. Para continuar, preciso do seu consentimento. As suas mensagens serão processadas por inteligência artificial e os seus dados serão anonimizados em conformidade com o RGPD. Responda SIM para aceitar."

### Active sender

Routed to Claude AI assistant as normal.

### Opted-out sender

Sent in the user's preferred language.

- **FR:** "Vous vous êtes désabonné(e). Vos données anonymisées sont conservées. Pour vous réinscrire, envoyez REJOINDRE."
- **EN:** "You have unsubscribed. Your anonymised data is retained. To re-subscribe, send JOIN."
- **ES:** "Se ha dado de baja. Sus datos anonimizados se conservan. Para volver a suscribirse, envíe UNIRSE."
- **PT:** "Cancelou a subscrição. Os seus dados anonimizados são conservados. Para se reinscrever, envie JUNTAR."

### Re-opt-in

Transitions user back to `active`, updates `consent_given_at`, clears `consent_revoked_at`. Assistant responds with a welcome-back message in their preferred language:

- **FR:** "Bon retour ! Votre accès à l'assistant #BuildingResilience est réactivé. Comment puis-je vous aider ?"
- **EN:** "Welcome back! Your access to the #BuildingResilience assistant has been reactivated. How can I help you?"
- **ES:** "Bienvenido/a de nuevo. Su acceso al asistente #BuildingResilience ha sido reactivado. ¿En qué puedo ayudarle?"
- **PT:** "Bem-vindo/a de volta! O seu acesso ao assistente #BuildingResilience foi reativado. Como posso ajudá-lo/a?"

## Data Model Changes

New columns added to the existing registration table (no separate table needed):

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| `consent_status` | text | `'registered'` | One of: `registered`, `active`, `opted_out` |
| `consent_given_at` | timestamptz | null | Timestamp when user replied with consent keyword |
| `consent_revoked_at` | timestamptz | null | Timestamp when user sent opt-out keyword |
| `phone_hash` | text | — | SHA-256 hash of phone number (used for webhook lookup) |

Note: `phone_hash` may already exist on the registration table. If so, reuse it.

The `unknown` state is represented by the absence of a row in the registration table.

## Webhook Lookup Flow

On every incoming message:

1. Compute SHA-256 hash of sender phone number
2. Query: `SELECT consent_status, language FROM [registration_table] WHERE phone_hash = ?`
3. No row returned → unknown → send rejection message in French
4. Row found → route based on `consent_status`:
   - `registered` → check if message is a consent keyword → if yes, transition to `active`; if no, re-send consent prompt
   - `active` → route to Claude AI assistant
   - `opted_out` → check if message is a re-opt-in keyword → if yes, transition to `active`; if no, send opt-out reminder

## Opt-Out Handling

- Active users can send STOP/ARRÊTER/ARRETER/PARAR at any time
- `consent_status` set to `opted_out`, `consent_revoked_at` set to current timestamp
- Anonymised conversation data in `wa_conversations` and `wa_messages` is retained for analytics
- Confirmation message sent in user's preferred language

## Integration with Existing Roadmap

This feature spans multiple roadmap components:
- **WA-B02 (webhook handler):** Phone hash lookup and state routing logic
- **WA-B04 (Claude integration):** Only invoked for `active` users
- **WA-B07 (Supabase logging):** Consent state changes logged
- **WA-C01 (system prompt):** No impact — opt-in is handled before Claude is invoked

Suggested new feature IDs:
- **WA-B13:** Opt-in flow — consent state machine, trigger word matching, message routing
- **WA-B14:** Opt-out/re-opt-in handling
