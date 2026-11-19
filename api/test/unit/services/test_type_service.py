import hashlib
import hmac
import json
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask
from pydantic import SecretStr

from clue.constants.supported_types import SUPPORTED_TYPES
from clue.models.config import ExternalSource
from clue.services import type_service


def test_all_supported_types_skips_sources_above_user_classification():
    app = Flask(__name__)
    public_source = ExternalSource(name="public", url="http://public/", classification="TLP:CLEAR")
    restricted_source = ExternalSource(name="restricted", url="http://restricted/", classification="TLP:AMBER+STRICT")
    user = {"uname": "test-user", "classification": "TLP:CLEAR"}

    with (
        app.test_request_context(),
        patch.object(type_service, "config") as configuration,
        patch(
            "clue.services.type_service.CLASSIFICATION.is_accessible",
            side_effect=lambda _user_classification, source_classification: source_classification == "TLP:CLEAR",
        ) as is_accessible,
        patch("clue.services.type_service.get_obo_access_token", return_value=(None, None)) as get_obo,
        patch(
            "clue.services.type_service.get_supported_types",
            return_value={"ipv4": "TLP:CLEAR"},
        ) as get_types,
    ):
        configuration.api.external_sources = [public_source, restricted_source]
        result = type_service.all_supported_types(user)

    assert result == {"public": {"ipv4": "TLP:CLEAR"}}
    assert is_accessible.call_args_list == [
        (("TLP:CLEAR", "TLP:CLEAR"),),
        (("TLP:CLEAR", "TLP:AMBER+STRICT"),),
    ]
    get_obo.assert_called_once_with(public_source, user)
    get_types.assert_called_once_with(public_source.url, access_token=None, obo_access_token=None)


@pytest.mark.parametrize("getter", [type_service.get_types_regular_expressions, type_service.get_types_detection])
def test_detection_filters_inaccessible_types(getter):
    user = {"classification": "TLP:CLEAR"}
    with (
        patch.object(
            type_service, "all_supported_types", return_value={"plugin": {"domain": "TLP:CLEAR", "md5": "SECRET"}}
        ),
        patch.object(type_service.CLASSIFICATION, "is_accessible", side_effect=lambda _, c: c == "TLP:CLEAR"),
    ):
        result = getter(user)
    assert list(result) == ["domain"]


def test_v1_retains_regex_and_null_values_in_plugin_discovery_order():
    source_types = {"plugin": {"ja3": "TLP:CLEAR", "ip": "TLP:CLEAR", "md5": "TLP:CLEAR"}}
    with patch.object(type_service, "all_supported_types", return_value=source_types):
        result = type_service.get_types_regular_expressions({"classification": "TLP:CLEAR"})
    assert list(result) == ["ja3", "ip", "md5"]
    assert result == {"ja3": SUPPORTED_TYPES["ja3"]["regex"], "ip": None, "md5": SUPPORTED_TYPES["md5"]["regex"]}


def test_v2_returns_metadata_in_registry_order_with_optional_priority():
    source_types = {"plugin": {"ja3": "TLP:CLEAR", "md5": "TLP:CLEAR", "ip": "TLP:CLEAR", "ipv4": "TLP:CLEAR"}}
    with patch.object(type_service, "all_supported_types", return_value=source_types):
        result = type_service.get_types_detection({"classification": "TLP:CLEAR"})
    assert list(result) == ["ipv4", "ip", "md5", "ja3"]
    assert result["ipv4"]["priority"] == 10
    assert result["ip"] == {"regex": None, "case_sensitive": False}
    assert "priority" not in result["md5"]
    assert result["md5"] is not SUPPORTED_TYPES["md5"]


@pytest.mark.parametrize("getter", [type_service.get_types_regular_expressions, type_service.get_types_detection])
def test_detection_without_accessible_plugins_is_empty(getter):
    with patch.object(type_service, "all_supported_types", return_value={}):
        assert getter({"classification": "TLP:CLEAR"}) == {}


TEST_HMAC_SECRET = "00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff"
SOURCE_URL = "http://plugin.internal"
TYPES_URL = f"{SOURCE_URL}/types/"
PRODUCTION_CACHE_TIMEOUT = 5 * 60


class FakeRedis:
    """Minimal in-memory Redis replacement with a controllable clock for TTL testing."""

    def __init__(self):
        self.now = 0.0
        self.store: dict[str, tuple[str, float | None]] = {}

    def _alive(self, key):
        if key not in self.store:
            return False
        _, expires_at = self.store[key]
        if expires_at is not None and self.now >= expires_at:
            del self.store[key]
            return False
        return True

    def get(self, key):
        return self.store[key][0] if self._alive(key) else None

    def set(self, key, value, ex=None):
        self.store[key] = (value, self.now + ex if ex is not None else None)

    def expire(self, key, ttl):
        if self._alive(key):
            self.store[key] = (self.store[key][0], self.now + ttl)

    def keys(self, pattern):
        return [key for key in list(self.store) if self._alive(key)]

    def delete(self, key):
        self.store.pop(key, None)


@pytest.fixture(params=[None, TEST_HMAC_SECRET], ids=["without_hmac_secret", "with_hmac_secret"])
def hmac_secret(request):
    secret = SecretStr(request.param) if request.param else None
    with patch.object(type_service.config.api, "type_cache_hmac_secret", secret):
        yield request.param


@pytest.fixture
def fake_redis():
    redis = FakeRedis()
    with (
        patch.object(type_service.CACHE, "c", redis),
        patch.object(type_service.CACHE, "ttl", PRODUCTION_CACHE_TIMEOUT),
        patch.object(type_service, "DISABLE_CACHE", False),
    ):
        yield redis


@pytest.fixture
def plugin_request():
    """Mock the plugin so the response echoes the token it was called with."""

    def _respond(_method, _url, headers, **_kwargs):
        response = MagicMock(status_code=200)
        response.json.return_value = {"api_response": {"who": headers.get("Authorization")}}
        return response

    with patch.object(type_service, "request_with_safe_redirects", side_effect=_respond) as mock_request:
        yield mock_request


def test_cache_hash_without_secret_is_plain_sha256():
    with patch.object(type_service.config.api, "type_cache_hmac_secret", None):
        result = type_service._get_cache_key(TYPES_URL, "token-a", "obo-a")

    expected = hashlib.sha256(json.dumps([TYPES_URL, "token-a", "obo-a"]).encode("utf-8")).hexdigest()
    assert result == expected


def test_cache_hash_with_secret_is_hmac_sha256():
    with patch.object(type_service.config.api, "type_cache_hmac_secret", SecretStr(TEST_HMAC_SECRET)):
        result = type_service._get_cache_key(TYPES_URL, "token-a", "obo-a")

    expected = hmac.new(
        bytes.fromhex(TEST_HMAC_SECRET),
        json.dumps([TYPES_URL, "token-a", "obo-a"]).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    assert result == expected
    assert result != hashlib.sha256(json.dumps([TYPES_URL, "token-a", "obo-a"]).encode("utf-8")).hexdigest()


def test_cache_hash_depends_on_secret_value():
    with patch.object(type_service.config.api, "type_cache_hmac_secret", SecretStr(TEST_HMAC_SECRET)):
        first = type_service._get_cache_key(TYPES_URL, "token-a", None)
    with patch.object(type_service.config.api, "type_cache_hmac_secret", SecretStr("ff" * 32)):
        second = type_service._get_cache_key(TYPES_URL, "token-a", None)

    assert first != second


@pytest.mark.parametrize(
    "other",
    [
        ("http://other.internal/types/", "token-a", "obo-a"),
        (TYPES_URL, "token-b", "obo-a"),
        (TYPES_URL, "token-a", "obo-b"),
        (TYPES_URL, None, "obo-a"),
        (TYPES_URL, "token-a", None),
        (TYPES_URL, "obo-a", "token-a"),
    ],
)
def test_cache_hash_differs_per_url_and_token(hmac_secret, other):
    base = type_service._get_cache_key(TYPES_URL, "token-a", "obo-a")

    assert base == type_service._get_cache_key(TYPES_URL, "token-a", "obo-a")
    assert base != type_service._get_cache_key(*other)


def test_different_tokens_get_their_own_response(hmac_secret, fake_redis, plugin_request):
    result_a = type_service.get_supported_types(SOURCE_URL, access_token="userA-token")
    result_b = type_service.get_supported_types(SOURCE_URL, access_token="userB-token")

    assert result_a == {"who": "Bearer userA-token"}
    assert result_b == {"who": "Bearer userB-token"}
    assert plugin_request.call_count == 2
    assert len(fake_redis.store) == 2


def test_different_obo_tokens_get_their_own_response(hmac_secret, fake_redis, plugin_request):
    result_a = type_service.get_supported_types(SOURCE_URL, access_token="shared", obo_access_token="obo-A")
    result_b = type_service.get_supported_types(SOURCE_URL, access_token="shared", obo_access_token="obo-B")

    assert result_a == {"who": "Bearer obo-A"}
    assert result_b == {"who": "Bearer obo-B"}
    assert plugin_request.call_count == 2


def test_same_token_reuses_cache(hmac_secret, fake_redis, plugin_request):
    first = type_service.get_supported_types(SOURCE_URL, access_token="userA-token")
    second = type_service.get_supported_types(SOURCE_URL, access_token="userA-token")

    assert first == second == {"who": "Bearer userA-token"}
    assert plugin_request.call_count == 1


def test_cache_key_does_not_expose_url_or_token(hmac_secret, fake_redis, plugin_request):
    type_service.get_supported_types(SOURCE_URL, access_token="userA-token", obo_access_token="obo-A")

    [key] = fake_redis.store
    assert key == f"clue_types-{type_service._get_cache_key(TYPES_URL, 'userA-token', 'obo-A')}"
    assert TYPES_URL not in key
    assert "userA-token" not in key
    assert "obo-A" not in key


def test_cache_expires_after_timeout(hmac_secret, fake_redis, plugin_request):
    type_service.get_supported_types(SOURCE_URL, access_token="userA-token")

    fake_redis.now = PRODUCTION_CACHE_TIMEOUT - 1
    type_service.get_supported_types(SOURCE_URL, access_token="userA-token")
    assert plugin_request.call_count == 1

    fake_redis.now = PRODUCTION_CACHE_TIMEOUT
    type_service.get_supported_types(SOURCE_URL, access_token="userA-token")
    assert plugin_request.call_count == 2


def test_cache_expires_after_timeout_even_when_used(hmac_secret, fake_redis, plugin_request):
    """Cache hits must not extend the lifetime: access and plugin changes need to be re-validated."""
    type_service.get_supported_types(SOURCE_URL, access_token="userA-token")

    for elapsed in range(1, PRODUCTION_CACHE_TIMEOUT):
        fake_redis.now = elapsed
        type_service.get_supported_types(SOURCE_URL, access_token="userA-token")
    assert plugin_request.call_count == 1

    fake_redis.now = PRODUCTION_CACHE_TIMEOUT
    type_service.get_supported_types(SOURCE_URL, access_token="userA-token")
    assert plugin_request.call_count == 2


def test_cache_get_refreshes_ttl_by_default(fake_redis):
    type_service.CACHE.set("key", {"value": "cached"})
    fake_redis.now = PRODUCTION_CACHE_TIMEOUT - 1
    assert type_service.CACHE.get("key") == {"value": "cached"}
    fake_redis.now = PRODUCTION_CACHE_TIMEOUT
    assert type_service.CACHE.get("key") == {"value": "cached"}


def test_disable_cache_always_polls_plugin(hmac_secret, fake_redis, plugin_request):
    with patch.object(type_service, "DISABLE_CACHE", True):
        type_service.get_supported_types(SOURCE_URL, access_token="userA-token")
        type_service.get_supported_types(SOURCE_URL, access_token="userA-token")

    assert plugin_request.call_count == 2
