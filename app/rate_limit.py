import time

RATE_LIMIT_MAX_MESSAGES = 10
RATE_LIMIT_WINDOW_SECONDS = 60

# In-memory sliding window — correct for single-process deploys (Railway
# default). If this app is ever scaled to multiple workers/replicas, move
# this state to Supabase or Redis so limits are enforced globally.
_message_log: dict[str, list[float]] = {}

RATE_LIMIT_MESSAGES = {
    "fr": (
        "Vous envoyez des messages trop rapidement. "
        "Veuillez patienter un moment avant de réessayer."
    ),
    "en": (
        "You're sending messages too quickly. "
        "Please wait a moment before trying again."
    ),
}


def check_rate_limit(phone_hash: str) -> bool:
    """Check if a user is within their rate limit.

    Returns True if allowed, False if rate-limited.
    Uses an in-memory sliding window: up to RATE_LIMIT_MAX_MESSAGES
    messages per RATE_LIMIT_WINDOW_SECONDS per user.
    """
    now = time.time()
    cutoff = now - RATE_LIMIT_WINDOW_SECONDS

    timestamps = _message_log.get(phone_hash, [])
    timestamps = [t for t in timestamps if t > cutoff]

    if len(timestamps) >= RATE_LIMIT_MAX_MESSAGES:
        _message_log[phone_hash] = timestamps
        return False

    timestamps.append(now)
    _message_log[phone_hash] = timestamps
    return True


def rate_limit_message(language: str) -> str:
    """Return a polite rate-limit message in the user's language."""
    return RATE_LIMIT_MESSAGES.get(language, RATE_LIMIT_MESSAGES["fr"])
