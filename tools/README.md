# Operator Agent CLI

Interactive tool for managing escalated WhatsApp conversations. Uses Claude to draft responses, then sends them via the cadidi API.

## Prerequisites

- cadidi server running (`uvicorn main:app --reload`)
- `.env` file with: `SUPABASE_URL`, `SUPABASE_KEY`, `ANTHROPIC_API_KEY`, `BROADCAST_API_KEY`
- Optional: `CADIDI_API_URL` (defaults to `http://localhost:8000`)

## Usage

```bash
cd /home/chomei/bomalab/cadidi
source .venv/bin/activate
python tools/operator.py
```

## How It Works

1. The tool lists all open escalations (conversations where Claude flagged a human should take over)
2. You pick one — the tool shows the full conversation history and why Claude escalated
3. Claude drafts a suggested response
4. You choose:
   - **a** (approve) — send the draft as-is
   - **e** (edit) — modify the draft, then send
   - **r** (reject) — Claude generates a new draft
   - **s** (skip) — go back to the list without acting
5. After sending, you're asked whether to resolve (close) the escalation
   - **y** — the user's next message goes back to Claude
   - **n** — the escalation stays open (you can send more messages)

## Commands in the Main Menu

| Key | Action |
|-----|--------|
| `1`, `2`, ... | Select an escalation by number |
| `r` | Refresh the escalation list |
| `q` | Quit |

## What Triggers an Escalation

Claude is instructed to escalate when:
- VIP logistics requests
- Complaints
- Medical or security concerns
- Requests for personal contact with speakers or dignitaries
- Questions Claude can't confidently answer from the knowledge base

Users can also trigger escalation by asking to "speak to a human" / "parler à quelqu'un".

## Architecture

```
tools/operator.py
  ├── reads from Supabase (wa_escalations, wa_messages, registrations)
  ├── calls Claude API to draft responses
  └── calls cadidi API (/respond, /resolve) to send messages and close escalations
```

The tool reads directly from Supabase for speed, but writes go through the cadidi API so that messages are properly saved to conversation history and sent via Twilio.
