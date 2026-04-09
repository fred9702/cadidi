"""Operator agent CLI — manage escalated WhatsApp conversations with Claude-assisted drafts."""

import anthropic
import httpx
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
        reg = (
            supabase.table("registrations")
            .select("phone")
            .eq("phone_hash", esc["phone_hash"])
            .execute()
        )
        phone = reg.data[0]["phone"] if reg.data else None

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


def main():
    """Interactive operator loop."""
    from decouple import config
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
            try:
                draft = draft_response(
                    claude, history, esc.get("reason", ""), esc.get("language", "fr")
                )
            except Exception as e:
                print(f"Error generating draft: {e}")
                action = input("[r]etry / [s]kip: ").strip().lower()
                if action == "s":
                    break
                continue

            print(f"\n--- Draft ---\n{draft}\n--- End Draft ---\n")

            action = input("[a]pprove / [e]dit / [r]eject (new draft) / [s]kip: ").strip().lower()

            if action == "s":
                break

            if action == "r":
                continue

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
                print(f"\nSending to {esc['phone']}...")
                success, detail = send_response(api_url, api_key, esc["phone"], draft)
                if success:
                    print("Sent successfully.")
                else:
                    print(f"Failed to send: {detail}")
                    break

                resolve = input("\nResolve this escalation? [y/n]: ").strip().lower()
                if resolve == "y":
                    success, detail = resolve_escalation(api_url, api_key, esc["phone"])
                    if success:
                        print("Escalation resolved.")
                    else:
                        print(f"Failed to resolve: {detail}")
                break

        print()


if __name__ == "__main__":
    main()
