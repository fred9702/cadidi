import hashlib


def hash_phone_number(phone: str) -> str:
    """SHA-256 hash of a phone number. Strips whitespace before hashing."""
    return hashlib.sha256(phone.strip().encode("utf-8")).hexdigest()
