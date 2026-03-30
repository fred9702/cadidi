# Railway Deployment Design — #BuildingResilience WhatsApp Platform

## Overview

Deploy the FastAPI WhatsApp AI assistant to Railway using Nixpacks (auto-detect Python). Auto-deploy from `main` branch via GitHub integration. CLI-driven setup.

## Constraints

- Railway CLI for all setup (no dashboard)
- Nixpacks builder (no Dockerfile)
- Auto-deploy on push to `main` via GitHub repo `fred9702/cadidi`
- 6 environment variables (secrets set interactively by operator)
- `/health` endpoint already exists for healthchecks
- Python 3.10 runtime

## Railway Project Setup

All via CLI:

1. Install Railway CLI
2. `railway login` — interactive auth
3. `railway init` — create project
4. Connect GitHub repo `fred9702/cadidi` with auto-deploy on `main`
5. Set environment variables via `railway variables set`

## App Configuration

**Start command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`

Railway injects a `PORT` env var. The app must bind to `0.0.0.0` (not localhost) on that port.

**Config file:** `railway.json` at project root:

```json
{
  "$schema": "https://railway.com/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "uvicorn main:app --host 0.0.0.0 --port $PORT",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 30,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 3
  }
}
```

**Python version:** `runtime.txt` with `python-3.10.13` to pin the version.

## Environment Variables

Set interactively by operator (never committed to repo):

- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_NUMBER`
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `ANTHROPIC_API_KEY`

## Files to Create

| File | Purpose |
|------|---------|
| `railway.json` | Railway deployment config (start command, healthcheck, restart policy) |
| `runtime.txt` | Pin Python version to 3.10.13 |

## Post-Deploy

After Railway assigns a public URL:

1. Verify `/health` returns `{"status": "ok"}`
2. Update Twilio webhook URL to `https://<railway-url>/message` (roadmap WA-E06)

## Integration with Roadmap

- **WA-B11 (Production deployment):** This spec covers it
- **WA-E06 (Production webhook cutover):** Swapping Twilio webhook URL to Railway URL (manual step post-deploy)
