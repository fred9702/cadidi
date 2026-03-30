from app.consent.hashing import hash_phone_number


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
