from unittest.mock import patch

from app.broadcast.auth import verify_api_key


@patch("app.broadcast.auth.config", return_value="correct-secret-key")
def test_verify_valid_key(mock_config):
    assert verify_api_key("correct-secret-key") is True


@patch("app.broadcast.auth.config", return_value="correct-secret-key")
def test_verify_invalid_key(mock_config):
    assert verify_api_key("wrong-key") is False


@patch("app.broadcast.auth.config", return_value="correct-secret-key")
def test_verify_empty_key(mock_config):
    assert verify_api_key("") is False


@patch("app.broadcast.auth.config", return_value="correct-secret-key")
def test_verify_timing_safe(mock_config):
    """Verify we use secrets.compare_digest (timing-safe comparison)."""
    import secrets
    with patch("app.broadcast.auth.secrets.compare_digest", wraps=secrets.compare_digest) as mock_compare:
        verify_api_key("some-key")
        mock_compare.assert_called_once()
