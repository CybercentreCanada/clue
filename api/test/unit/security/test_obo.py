from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from clue.common.exceptions import InvalidDataException
from clue.security.obo import (
    _get_obo_token_store,
    _get_token_raw,
    get_obo_token,
    try_validate_expiry,
)


# Test _get_obo_token_store function
@patch("clue.security.obo.get_redis")
@patch("clue.security.obo.ExpiringSet")
def test_get_obo_token_store_creates_correct_key(mock_expiring_set, mock_get_redis):
    """Test that the token store is created with the correct key format."""
    mock_redis = Mock()
    mock_get_redis.return_value = mock_redis

    _get_obo_token_store("test-service", "test-user")

    mock_expiring_set.assert_called_once_with(
        "test-service_token_test-user",
        host=mock_redis,
        ttl=300,  # 60 * 5
    )


@patch("clue.security.obo.get_redis")
@patch("clue.security.obo.ExpiringSet")
def test_get_obo_token_store_ttl(mock_expiring_set, mock_get_redis):
    """Test that the TTL is set to 5 minutes (300 seconds)."""
    _get_obo_token_store("service", "user")

    args, kwargs = mock_expiring_set.call_args
    assert kwargs["ttl"] == 300


# Test _get_token_raw function
@patch("clue.security.obo._get_obo_token_store")
def test_get_token_raw_returns_token_when_available(mock_get_store):
    """Test that a token is returned when available in the store."""
    mock_store = Mock()
    mock_store.length.return_value = 1
    mock_store.random.return_value = ["test-token"]
    mock_get_store.return_value = mock_store

    result = _get_token_raw("service", "user")

    assert result == "test-token"
    mock_store.random.assert_called_once_with(1)


@patch("clue.security.obo._get_obo_token_store")
def test_get_token_raw_returns_none_when_empty(mock_get_store):
    """Test that None is returned when no tokens are available."""
    mock_store = Mock()
    mock_store.length.return_value = 0
    mock_get_store.return_value = mock_store

    result = _get_token_raw("service", "user")

    assert result is None
    mock_store.random.assert_not_called()


# Test try_validate_expiry function
@patch("clue.security.obo.decode_jwt_payload")
def test_try_validate_expiry_valid_token(mock_decode):
    """Test that a valid, non-expired token is returned unchanged."""
    future_time = datetime.now() + timedelta(hours=1)
    mock_decode.return_value = {"exp": future_time.timestamp()}

    token = "valid-token"
    result = try_validate_expiry(token)

    assert result == token


@patch("clue.security.obo.decode_jwt_payload")
def test_try_validate_expiry_expired_token(mock_decode):
    """Test that an expired token returns None."""
    past_time = datetime.now() - timedelta(hours=1)
    mock_decode.return_value = {"exp": past_time.timestamp()}

    token = "expired-token"
    result = try_validate_expiry(token)

    assert result is None


@patch("clue.security.obo.decode_jwt_payload")
def test_try_validate_expiry_missing_exp_field(mock_decode):
    """Test that a token without 'exp' field is returned unchanged."""
    mock_decode.return_value = {"sub": "user"}

    token = "token-without-exp"
    result = try_validate_expiry(token)

    assert result == token


@patch("clue.security.obo.decode_jwt_payload")
def test_try_validate_expiry_non_jwt_token(mock_decode):
    """Test that a non-JWT token raises IndexError and is returned unchanged."""
    mock_decode.side_effect = IndexError("Not a JWT")

    token = "non-jwt-token"
    result = try_validate_expiry(token)

    assert result == token


# Test get_obo_token function
@patch("clue.security.obo.config")
def test_get_obo_token_invalid_service(mock_config):
    """Test that InvalidDataException is raised for invalid service."""
    mock_config.api.obo_targets = ["valid-service"]

    with pytest.raises(InvalidDataException, match="Not a valid OBO target"):
        get_obo_token("invalid-service", "token", "user")


@patch("clue.security.obo.config")
def test_get_obo_token_test_obo_service(mock_config):
    """Test that test-obo service returns the access token unchanged."""
    mock_config.api.obo_targets = ["test-obo"]

    result = get_obo_token("test-obo", "access-token", "user")

    assert result == "access-token"


@patch("clue.security.obo.config")
@patch("clue.security.obo._get_token_raw")
@patch("clue.security.obo.try_validate_expiry")
def test_get_obo_token_uses_cached_token(mock_validate, mock_get_raw, mock_config):
    """Test that cached token is used when available and valid."""
    mock_config.api.obo_targets = ["service"]
    mock_get_raw.return_value = "cached-token"
    mock_validate.return_value = "cached-token"

    result = get_obo_token("service", "access-token", "user")

    assert result == "cached-token"
    mock_get_raw.assert_called_once_with("service", "user")
    mock_validate.assert_called_once_with("cached-token")


@patch("clue.security.obo.config")
@patch("clue.security.obo._get_token_raw")
@patch("clue.security.obo.try_validate_expiry")
def test_get_obo_token_expired_cached_token(mock_validate, mock_get_raw, mock_config):
    """Test that expired cached token triggers new token fetch."""
    mock_config.api.obo_targets = ["service"]
    mock_get_raw.return_value = "cached-token"
    mock_validate.return_value = None  # Token expired

    with patch("clue.security.obo.get_extensions") as mock_extensions:
        mock_extensions.return_value = []

        result = get_obo_token("service", "access-token", "user")

        assert result == "access-token"  # Falls back to provided token


@patch("clue.security.obo.config")
@patch("clue.security.obo._get_token_raw")
@patch("clue.security.obo.get_extensions")
@patch("clue.security.obo._get_obo_token_store")
def test_get_obo_token_with_extension(mock_get_store, mock_extensions, mock_get_raw, mock_config):
    """Test OBO token generation with extension."""
    mock_config.api.obo_targets = ["service"]
    mock_get_raw.return_value = None  # No cached token

    # Mock extension with OBO module
    mock_extension = Mock()
    mock_obo_module = Mock(return_value="new-obo-token")
    mock_extension.modules.obo_module = mock_obo_module
    mock_extensions.return_value = [mock_extension]

    # Mock token store
    mock_store = Mock()
    mock_get_store.return_value = mock_store

    result = get_obo_token("service", "access-token", "user")

    assert result == "new-obo-token"
    mock_obo_module.assert_called_once_with("service", "access-token", "user")
    mock_store.pop_all.assert_called_once()
    mock_store.add.assert_called_once_with("new-obo-token")


@patch("clue.security.obo.config")
@patch("clue.security.obo._get_token_raw")
@patch("clue.security.obo.get_extensions")
def test_get_obo_token_no_extension(mock_extensions, mock_get_raw, mock_config):
    """Test OBO token when no extension is available."""
    mock_config.api.obo_targets = ["service"]
    mock_get_raw.return_value = None

    # Mock extension without OBO module
    mock_extension = Mock()
    mock_extension.modules.obo_module = None
    mock_extensions.return_value = [mock_extension]

    result = get_obo_token("service", "access-token", "user")

    assert result == "access-token"  # Falls back to provided token


@patch("clue.security.obo.config")
@patch("clue.security.obo._get_token_raw")
@patch("clue.security.obo.get_extensions")
def test_get_obo_token_extension_fails(mock_extensions, mock_get_raw, mock_config):
    """Test OBO token when extension returns None."""
    mock_config.api.obo_targets = ["service"]
    mock_get_raw.return_value = None

    # Mock extension that returns None
    mock_extension = Mock()
    mock_obo_module = Mock(return_value=None)
    mock_extension.modules.obo_module = mock_obo_module
    mock_extensions.return_value = [mock_extension]

    result = get_obo_token("service", "access-token", "user")

    assert result is None


@patch("clue.security.obo.config")
@patch("clue.security.obo._get_token_raw")
def test_get_obo_token_force_refresh(mock_get_raw, mock_config):
    """Test that force_refresh bypasses cache."""
    mock_config.api.obo_targets = ["service"]

    with patch("clue.security.obo.get_extensions") as mock_extensions:
        mock_extensions.return_value = []

        result = get_obo_token("service", "access-token", "user", force_refresh=True)

        mock_get_raw.assert_not_called()  # Cache should be bypassed
        assert result == "access-token"


@patch("clue.security.obo.config")
@patch("clue.security.obo._get_token_raw")
def test_get_obo_token_exception_handling(mock_get_raw, mock_config):
    """Test that exceptions are handled gracefully."""
    mock_config.api.obo_targets = ["service"]
    mock_get_raw.side_effect = Exception("Redis error")

    result = get_obo_token("service", "access-token", "user")

    assert result is None


@patch("clue.security.obo.config")
@patch("clue.security.obo.get_redis")
@patch("clue.security.obo.ExpiringSet")
@patch("clue.security.obo.get_extensions")
def test_full_obo_flow_with_caching(mock_extensions, mock_expiring_set, mock_get_redis, mock_config):
    """Test the complete OBO flow with caching."""
    # Setup
    mock_config.api.obo_targets = ["target-service"]

    # Mock Redis store
    mock_store = Mock()
    mock_store.length.return_value = 0  # No cached token initially
    mock_expiring_set.return_value = mock_store

    # Mock extension
    mock_extension = Mock()
    mock_obo_module = Mock(return_value="fresh-obo-token")
    mock_extension.modules.obo_module = mock_obo_module
    mock_extensions.return_value = [mock_extension]

    # First call - should fetch new token
    result1 = get_obo_token("target-service", "access-token", "test-user")
    assert result1 == "fresh-obo-token"
    mock_store.add.assert_called_with("fresh-obo-token")

    # Second call - should use cached token
    mock_store.length.return_value = 1
    mock_store.random.return_value = ["fresh-obo-token"]

    with patch("clue.security.obo.try_validate_expiry", return_value="fresh-obo-token"):
        result2 = get_obo_token("target-service", "access-token", "test-user")
        assert result2 == "fresh-obo-token"


@patch("clue.security.obo.config")
@patch("clue.security.obo._get_token_raw")
@patch("clue.security.obo.get_extensions")
def test_get_obo_token_multiple_extensions_first_match(mock_extensions, mock_get_raw, mock_config):
    """Test that the first extension with obo_module is used."""
    mock_config.api.obo_targets = ["service"]
    mock_get_raw.return_value = None

    # Mock first extension without OBO module
    mock_extension1 = Mock()
    mock_extension1.modules.obo_module = None

    # Mock second extension with OBO module
    mock_extension2 = Mock()
    mock_obo_module = Mock(return_value="extension2-token")
    mock_extension2.modules.obo_module = mock_obo_module

    # Mock third extension with OBO module (should not be called)
    mock_extension3 = Mock()
    mock_extension3.modules.obo_module = Mock(return_value="extension3-token")

    mock_extensions.return_value = [mock_extension1, mock_extension2, mock_extension3]

    with patch("clue.security.obo._get_obo_token_store") as mock_get_store:
        mock_store = Mock()
        mock_get_store.return_value = mock_store

        result = get_obo_token("service", "access-token", "user")

        assert result == "extension2-token"
        mock_extension2.modules.obo_module.assert_called_once_with("service", "access-token", "user")
        mock_extension3.modules.obo_module.assert_not_called()


@patch("clue.security.obo.config")
@patch("clue.security.obo._get_token_raw")
@patch("clue.security.obo.try_validate_expiry")
def test_get_obo_token_cached_token_validation_flow(mock_validate, mock_get_raw, mock_config):
    """Test the flow when cached token exists but needs validation."""
    mock_config.api.obo_targets = ["service"]
    mock_get_raw.return_value = "cached-token"

    # First call: token is valid
    mock_validate.return_value = "cached-token"
    result1 = get_obo_token("service", "access-token", "user")
    assert result1 == "cached-token"

    # Second call: token is expired/invalid
    mock_validate.return_value = None
    with patch("clue.security.obo.get_extensions") as mock_extensions:
        mock_extensions.return_value = []
        result2 = get_obo_token("service", "access-token", "user")
        assert result2 == "access-token"  # Falls back to provided token


@patch("clue.security.obo.config")
@patch("clue.security.obo._get_token_raw")
@patch("clue.security.obo.get_extensions")
@patch("clue.security.obo._get_obo_token_store")
def test_get_obo_token_store_operations_on_success(mock_get_store, mock_extensions, mock_get_raw, mock_config):
    """Test that token store operations are called correctly on successful OBO."""
    mock_config.api.obo_targets = ["service"]
    mock_get_raw.return_value = None

    # Mock extension
    mock_extension = Mock()
    mock_obo_module = Mock(return_value="new-token")
    mock_extension.modules.obo_module = mock_obo_module
    mock_extensions.return_value = [mock_extension]

    # Mock token store
    mock_store = Mock()
    mock_get_store.return_value = mock_store

    result = get_obo_token("service", "access-token", "user")

    assert result == "new-token"
    # Verify store operations are called in correct order
    mock_store.pop_all.assert_called_once()
    mock_store.add.assert_called_once_with("new-token")
