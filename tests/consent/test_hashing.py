from app.consent.hashing import hash_phone_number, hash_email


def test_hash_phone_number_returns_sha256():
    result = hash_phone_number("+447700900000")
    assert len(result) == 64
    assert result.isalnum()


def test_hash_phone_number_is_deterministic():
    a = hash_phone_number("+447700900000")
    b = hash_phone_number("+447700900000")
    assert a == b


def test_hash_phone_number_different_numbers_differ():
    a = hash_phone_number("+447700900000")
    b = hash_phone_number("+447700900001")
    assert a != b


def test_hash_phone_number_strips_whitespace():
    a = hash_phone_number("+447700900000")
    b = hash_phone_number(" +447700900000 ")
    assert a == b


def test_hash_email_returns_sha256():
    result = hash_email("User@Example.com")
    assert len(result) == 64
    assert result.isalnum()


def test_hash_email_is_case_insensitive():
    a = hash_email("User@Example.com")
    b = hash_email("user@example.com")
    assert a == b


def test_hash_email_strips_whitespace():
    a = hash_email("user@example.com")
    b = hash_email("  User@Example.com  ")
    assert a == b


def test_hash_email_different_emails_differ():
    a = hash_email("alice@example.com")
    b = hash_email("bob@example.com")
    assert a != b
