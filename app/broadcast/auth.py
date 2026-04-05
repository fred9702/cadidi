import secrets

from decouple import config


def verify_api_key(api_key: str) -> bool:
    """Validate a broadcast API key using timing-safe comparison.

    Compares against the BROADCAST_API_KEY environment variable.
    Returns True if valid, False otherwise.
    """
    expected = config("BROADCAST_API_KEY")
    return secrets.compare_digest(api_key, expected)
