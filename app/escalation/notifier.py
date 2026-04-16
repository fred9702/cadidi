"""Send an alert email to operators whenever a new escalation is opened.

Uses Resend (https://resend.com). Requires:
  - RESEND_API_KEY: Resend API key
  - OPERATOR_EMAILS: comma-separated recipient list

Optional:
  - FROM_EMAIL: verified sender (default: noreply@send.resilience241.com)

All failures are swallowed and logged so that a Resend outage never
blocks the inbound WhatsApp flow — the escalation row is still created
in Supabase and operators can pick it up via the CLI.
"""

import logging
from html import escape as html_escape

import httpx
from decouple import config

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"
DEFAULT_FROM = "Cadidi Escalations <noreply@send.resilience241.com>"
REQUEST_TIMEOUT_SECONDS = 10.0


def _recipients() -> list[str]:
    raw = config("OPERATOR_EMAILS", default="")
    return [e.strip() for e in raw.split(",") if e.strip()]


def _build_text(reason: str | None, user_message: str, phone_hash: str) -> str:
    lines = [
        "A new escalation was opened in Cadidi.",
        "",
        f"Reason: {reason or '(not provided)'}",
        f"Phone hash: {phone_hash}",
        "",
        "Triggering message:",
        user_message,
        "",
        "Respond via the operator CLI:",
        "    python -m tools.operator",
    ]
    return "\n".join(lines)


def _build_html(reason: str | None, user_message: str, phone_hash: str) -> str:
    reason_html = html_escape(reason) if reason else "<em>(not provided)</em>"
    return (
        "<p>A new escalation was opened in <strong>Cadidi</strong>.</p>"
        f"<p><strong>Reason:</strong> {reason_html}<br>"
        f"<strong>Phone hash:</strong> <code>{html_escape(phone_hash)}</code></p>"
        "<p><strong>Triggering message:</strong></p>"
        f"<blockquote>{html_escape(user_message)}</blockquote>"
        "<p>Respond via the operator CLI: "
        "<code>python -m tools.operator</code></p>"
    )


def notify_operators(
    reason: str | None,
    user_message: str,
    phone_hash: str,
) -> None:
    """Send an escalation alert email to all configured operators.

    Never raises — all exceptions are logged.
    """
    try:
        api_key = config("RESEND_API_KEY", default="")
        if not api_key:
            logger.warning("RESEND_API_KEY not set; skipping escalation email")
            return

        recipients = _recipients()
        if not recipients:
            logger.warning("OPERATOR_EMAILS not set; skipping escalation email")
            return

        from_email = config("FROM_EMAIL", default=DEFAULT_FROM)

        subject_reason = reason or "new user request"
        payload = {
            "from": from_email,
            "to": recipients,
            "subject": f"[Cadidi] Escalation: {subject_reason}",
            "text": _build_text(reason, user_message, phone_hash),
            "html": _build_html(reason, user_message, phone_hash),
        }

        response = httpx.post(
            RESEND_API_URL,
            json=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        if response.status_code >= 400:
            logger.error(
                "Resend returned %s when sending escalation alert: %s",
                response.status_code,
                response.text,
            )
        else:
            logger.info("Escalation alert emailed to %d operator(s)", len(recipients))
    except Exception:
        logger.exception("Failed to send escalation alert email")
