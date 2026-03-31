import hashlib


def hash_phone_number(phone: str) -> str:
    """SHA-256 hash of a phone number. Strips whitespace before hashing."""
    return hashlib.sha256(phone.strip().encode("utf-8")).hexdigest()


def hash_email(email: str) -> str:
    """SHA-256 hash of an email. Lowercases, strips whitespace before hashing."""
    return hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()
