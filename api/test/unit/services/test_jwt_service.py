import time
from concurrent.futures import ThreadPoolExecutor
from threading import Event, current_thread
from types import SimpleNamespace
from unittest.mock import Mock, patch

import jwt
import pytest
import requests
from cryptography.hazmat.primitives.asymmetric import rsa
from flask import Flask
from pydantic import ValidationError

from clue.models.config import OAuth
from clue.models.jwks import JWKSSnapshot
from clue.services import jwt_service
from clue.services.jwt_service import extract_audience
from test.utils.oauth_credentials import get_token


@pytest.fixture
def service(monkeypatch):
    app = Flask(__name__)
    jwt_service.cache.init_app(app, config={"CACHE_TYPE": "SimpleCache"})
    monkeypatch.setattr(
        jwt_service.config.auth.oauth, "providers", {"provider": SimpleNamespace(jwks_uri="https://idp/jwks")}
    )
    monkeypatch.setattr(jwt_service.config.auth.oauth, "jwks_refresh_cooldown_seconds", 60)
    monkeypatch.setattr(jwt_service, "_last_jwks_refresh_time", None)
    monkeypatch.setattr(jwt_service, "_pinned_jwks", None)
    monkeypatch.setattr(time, "monotonic", Mock(return_value=100.0))
    with app.app_context():
        yield jwt_service


def token(kid):
    return jwt.encode({"sub": "user"}, "test-secret", algorithm="HS256", headers={"kid": kid})


def key(kid):
    return {"kid": kid, "kty": "oct", "k": "dGVzdC1zZWNyZXQ", "alg": "HS256"}


def snapshot(jwks, providers, fetched_at=100.0):
    return JWKSSnapshot(jwks, providers, {name: fetched_at for name in providers.values()})


def seed_cache(service):
    service.cache.set("get_jwks", snapshot({"known": key("known")}, {"known": "provider"}), timeout=43200)


def test_get_jwk_refreshes_the_cache_for_an_unknown_key(service):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    key_data = jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key(), as_dict=True) | {"kid": "new-key"}
    access_token = jwt.encode({"sub": "user"}, private_key, algorithm="RS256", headers={"kid": key_data["kid"]})

    with (
        patch.object(service.requests, "get", return_value=Mock(json=lambda: {"keys": [key_data]})) as fetch,
        patch.object(service.cache, "delete") as delete_cache,
    ):
        service.cache.set("get_jwks", JWKSSnapshot({}, {}, {}))
        result = service.get_jwk(access_token)

    assert result.key_id == key_data["kid"]
    delete_cache.assert_not_called()
    fetch.assert_called_once_with("https://idp/jwks", timeout=10)


@pytest.mark.parametrize("lookup,error", [("get_jwk", "ClueKeyError"), ("get_provider", "ClueValueError")])
def test_unknown_kids_fetch_at_most_once_without_eviction(service, lookup, error):
    seed_cache(service)
    with (
        patch.object(service.requests, "get", return_value=Mock(json=lambda: {"keys": [key("known")]})) as fetch,
        patch.object(service.cache, "delete", wraps=service.cache.delete) as delete,
    ):
        for index in range(10):
            with pytest.raises(getattr(service, error)):
                getattr(service, lookup)(token(f"unknown-{index}"))
        assert service.get_jwk(token("known")).key_id == "known"
        assert service.get_provider(token("known")) == "provider"
    assert fetch.call_count == 1
    delete.assert_not_called()


@pytest.mark.parametrize("lookup", ["get_jwk", "get_provider"])
def test_rotated_key_succeeds_on_first_miss(service, lookup, monkeypatch):
    seed_cache(service)
    with patch.object(
        service.requests,
        "get",
        side_effect=[Mock(json=lambda: {"keys": [key("known")]}), Mock(json=lambda: {"keys": [key("new")]})],
    ) as fetch:
        with pytest.raises(service.ClueKeyError):
            service.get_jwk(token("unknown"))
        monkeypatch.setattr(time, "monotonic", Mock(return_value=160.0))
        result = getattr(service, lookup)(token("new"))
        assert (result.key_id if lookup == "get_jwk" else result) == ("new" if lookup == "get_jwk" else "provider")
        assert service.get_jwk(token("new")).key_id == "new"
        assert service.get_provider(token("new")) == "provider"
    assert fetch.call_count == 2
    fetch.assert_called_with("https://idp/jwks", timeout=10)


def test_cooldown_allows_one_more_fetch_after_expiry(service):
    seed_cache(service)
    with (
        patch.object(time, "monotonic", return_value=100.0) as clock,
        patch.object(service.requests, "get", return_value=Mock(json=lambda: {"keys": [key("known")]})) as fetch,
    ):
        for index, now in enumerate([100.0, 159.0, 161.0, 162.0]):
            clock.return_value = now
            with pytest.raises(service.ClueKeyError):
                service.get_jwk(token(f"unknown-{index}"))
    assert fetch.call_count == 2


def test_failed_refresh_preserves_cache_and_starts_cooldown(service):
    seed_cache(service)
    with patch.object(service.requests, "get", side_effect=requests.Timeout) as fetch:
        with pytest.raises(requests.Timeout):
            service.get_jwk(token("unknown"))
        with pytest.raises(service.ClueKeyError):
            service.get_jwk(token("another-unknown"))
        assert service.get_jwk(token("known")).key_id == "known"
    assert fetch.call_count == 1


def test_cold_cache_fetch_is_also_debounced(service):
    with patch.object(service.requests, "get", return_value=Mock(json=lambda: {"keys": [key("known")]})) as fetch:
        for index in range(4):
            with pytest.raises(service.ClueKeyError):
                service.get_jwk(token(f"unknown-{index}"))
    assert fetch.call_count == 1


def test_overlapping_miss_fails_fast_while_cached_key_still_works(service):
    seed_cache(service)
    started = Event()
    release = Event()

    def fetch_keys(*args, **kwargs):
        started.set()
        assert release.wait(timeout=5)
        return Mock(json=lambda: {"keys": [key("new")]})

    def lookup_new_key():
        with service.cache.app.app_context():
            return service.get_jwk(token("new"))

    with (
        patch.object(service.requests, "get", side_effect=fetch_keys) as fetch,
        ThreadPoolExecutor(max_workers=1) as pool,
    ):
        future = pool.submit(lookup_new_key)
        try:
            assert started.wait(timeout=5)
            with pytest.raises(service.ClueKeyError):
                service.get_jwk(token("unknown"))
            with pytest.raises(service.ClueValueError):
                service.get_provider(token("another-unknown"))
            assert service.get_jwk(token("known")).key_id == "known"
        finally:
            release.set()
        assert future.result(timeout=5).key_id == "new"
    assert fetch.call_count == 1


def test_cold_cache_timeout_does_not_trigger_repeated_fetches(service):
    with patch.object(service.requests, "get", side_effect=requests.Timeout) as fetch:
        with pytest.raises(requests.Timeout):
            service.get_jwk(token("unknown"))
        with pytest.raises(service.ClueKeyError):
            service.get_jwk(token("another-unknown"))
        with pytest.raises(service.ClueValueError):
            service.get_provider(token("unknown-provider"))
    assert fetch.call_count == 1


def test_cold_cache_recovers_after_failed_fetch_cooldown(service):
    with (
        patch.object(time, "monotonic", return_value=100.0) as clock,
        patch.object(
            service.requests,
            "get",
            side_effect=[requests.Timeout, Mock(json=lambda: {"keys": [key("new")]})],
        ) as fetch,
    ):
        with pytest.raises(requests.Timeout):
            service.get_jwk(token("new"))
        with pytest.raises(service.ClueKeyError):
            service.get_jwk(token("new"))
        assert service.cache.get("get_jwks") is None
        clock.return_value = 161.0
        assert service.get_jwk(token("new")).key_id == "new"
    assert fetch.call_count == 2


def test_configured_cooldown_is_used(service, monkeypatch):
    monkeypatch.setattr(service.config.auth.oauth, "jwks_refresh_cooldown_seconds", 120)
    seed_cache(service)
    with (
        patch.object(time, "monotonic", return_value=100.0) as clock,
        patch.object(service.requests, "get", return_value=Mock(json=lambda: {"keys": [key("known")]})) as fetch,
    ):
        for index, now in enumerate([100.0, 161.0, 221.0]):
            clock.return_value = now
            with pytest.raises(service.ClueKeyError):
                service.get_jwk(token(f"unknown-{index}"))
            assert fetch.call_count == (1 if index < 2 else 2)


@pytest.mark.parametrize("evict_jwks", [False, True])
def test_cache_pressure_does_not_reset_cooldown(service, evict_jwks):
    seed_cache(service)
    with patch.object(service.requests, "get", return_value=Mock(json=lambda: {"keys": [key("known")]})) as fetch:
        with pytest.raises(service.ClueKeyError):
            service.get_jwk(token("unknown"))
        for index in range(505):
            service.cache.set(f"unrelated-{index}", True, timeout=86400 if evict_jwks else 1000)
        assert service.cache.get("unrelated-0") is None
        assert (service.cache.get("get_jwks") is None) == evict_jwks
        assert service._last_jwks_refresh_time == 100.0
        for index in range(10):
            with pytest.raises(service.ClueKeyError):
                service.get_jwk(token(f"unknown-{index}"))
            with pytest.raises(service.ClueValueError):
                service.get_provider(token(f"unknown-provider-{index}"))
        if not evict_jwks:
            assert service.decode(token("known"), algorithms=["HS256"]) == {"sub": "user"}
    assert fetch.call_count == 1


def test_wall_clock_changes_do_not_reset_cooldown(service):
    with (
        patch("cachelib.simple.time", return_value=100.0) as wall_clock,
        patch.object(service.requests, "get", return_value=Mock(json=lambda: {"keys": [key("known")]})) as fetch,
    ):
        seed_cache(service)
        for index, now in enumerate([100.0, -10000.0, 10000.0]):
            wall_clock.return_value = now
            with pytest.raises(service.ClueKeyError):
                service.get_jwk(token(f"unknown-{index}"))
        assert service._last_jwks_refresh_time == 100.0
        assert service.decode(token("known"), algorithms=["HS256"]) == {"sub": "user"}
    assert fetch.call_count == 1


def test_first_fetch_at_monotonic_zero_is_debounced(service, monkeypatch):
    monkeypatch.setattr(time, "monotonic", Mock(return_value=0.0))
    with patch.object(service.requests, "get", return_value=Mock(json=lambda: {"keys": [key("known")]})) as fetch:
        for index in range(10):
            with pytest.raises(service.ClueKeyError):
                service.get_jwk(token(f"unknown-{index}"))
    assert service._last_jwks_refresh_time == 0.0
    assert fetch.call_count == 1


def _in_app(service, func, *args):
    with service.cache.app.app_context():
        return func(*args)


@pytest.mark.parametrize("lookup", ["get_jwk", "get_provider"])
def test_concurrent_unknown_kids_trigger_one_outbound_call(service, lookup):
    seed_cache(service)

    def fetch_keys(*args, **kwargs):
        time.sleep(0.05)  # hold the lock so other threads overlap with the fetch
        return Mock(json=lambda: {"keys": [key("known")]})

    def attempt(index):
        try:
            _in_app(service, getattr(service, lookup), token(f"unknown-{index}"))
        except (service.ClueKeyError, service.ClueValueError):
            return "rejected"
        return "accepted"

    with (
        patch.object(service.requests, "get", side_effect=fetch_keys) as fetch,
        ThreadPoolExecutor(max_workers=64) as pool,
    ):
        results = list(pool.map(attempt, range(60)))

    assert results == ["rejected"] * 60
    assert fetch.call_count == 1


def test_concurrent_unknown_kids_do_not_block_known_keys(service):
    seed_cache(service)

    def fetch_keys(*args, **kwargs):
        time.sleep(0.05)
        return Mock(json=lambda: {"keys": [key("known")]})

    def attempt(index):
        if index % 2:
            return _in_app(service, service.get_jwk, token("known")).key_id
        try:
            _in_app(service, service.get_jwk, token(f"unknown-{index}"))
        except service.ClueKeyError:
            return "rejected"

    with (
        patch.object(service.requests, "get", side_effect=fetch_keys) as fetch,
        ThreadPoolExecutor(max_workers=64) as pool,
    ):
        results = list(pool.map(attempt, range(60)))

    assert results == [("known" if index % 2 else "rejected") for index in range(60)]
    assert fetch.call_count == 1


def test_multiple_providers_are_fetched_once_per_debounced_lookup(service, monkeypatch):
    uris = {f"provider-{n}": f"https://idp-{n}/jwks" for n in range(4)}
    monkeypatch.setattr(
        service.config.auth.oauth,
        "providers",
        {name: SimpleNamespace(jwks_uri=uri) for name, uri in uris.items()},
    )
    keys_by_uri = {uri: {"keys": [key(f"kid-{name}")]} for name, uri in uris.items()}

    def fetch_keys(uri, timeout):
        time.sleep(0.01)
        return Mock(json=lambda: keys_by_uri[uri])

    def attempt(index):
        try:
            _in_app(service, service.get_jwk, token(f"unknown-{index}"))
        except service.ClueKeyError:
            return "rejected"

    with (
        patch.object(service.requests, "get", side_effect=fetch_keys) as fetch,
        ThreadPoolExecutor(max_workers=64) as pool,
    ):
        results = list(pool.map(attempt, range(60)))
        # Every provider's keys are usable and mapped to the right provider.
        for name in uris:
            assert service.get_jwk(token(f"kid-{name}")).key_id == f"kid-{name}"
            assert service.get_provider(token(f"kid-{name}")) == name

    assert results == ["rejected"] * 60
    assert sorted(call.args[0] for call in fetch.call_args_list) == sorted(uris.values())


def test_pinned_keys_survive_cache_eviction_during_cooldown(service):
    seed_cache(service)
    with patch.object(service.requests, "get", return_value=Mock(json=lambda: {"keys": [key("known")]})) as fetch:
        with pytest.raises(service.ClueKeyError):
            service.get_jwk(token("unknown"))
        assert service._pinned_jwks is not None

        # Fill SimpleCache with long-lived dummy keys until the JWKS entry is evicted.
        for index in range(505):
            service.cache.set(f"dummy-{index}", True, timeout=86400)
        assert service.cache.get("get_jwks") is None

        # Still inside the cooldown: legitimate tokens must verify and no fetch may occur.
        assert service.get_jwk(token("known")).key_id == "known"
        assert service.get_provider(token("known")) == "provider"
        assert service.decode(token("known"), algorithms=["HS256"]) == {"sub": "user"}
        with pytest.raises(service.ClueKeyError):
            service.get_jwk(token("still-unknown"))
    assert fetch.call_count == 1


def test_pinned_keys_serve_known_kid_when_cache_is_evicted_and_fetch_lock_is_held(service):
    service._pinned_jwks = snapshot({"known": key("known")}, {"known": "provider"})
    assert service.cache.get("get_jwks") is None
    assert service._jwks_refresh_lock.acquire(blocking=False)
    try:
        with patch.object(service.requests, "get") as fetch:
            assert service.get_jwk(token("known")).key_id == "known"
            with pytest.raises(service.ClueKeyError):
                service.get_jwk(token("unknown"))
    finally:
        service._jwks_refresh_lock.release()
    fetch.assert_not_called()


def test_empty_authoritative_response_clears_pinned_keys(service):
    seed_cache(service)
    service._pinned_jwks = snapshot({"known": key("known")}, {"known": "provider"})
    with patch.object(service.requests, "get", return_value=Mock(json=lambda: {"keys": []})) as fetch:
        with pytest.raises(service.ClueKeyError):
            service.get_jwk(token("unknown"))
        assert service._pinned_jwks.jwks == {}
        assert service.cache.get("get_jwks").jwks == {}

        # Evicting the cache must not resurrect the revoked key.
        service.cache.delete("get_jwks")
        with pytest.raises(service.ClueKeyError):
            service.get_jwk(token("known"))
    assert fetch.call_count == 1


def test_pinned_keys_older_than_max_stale_age_are_not_served(service, monkeypatch):
    service._pinned_jwks = snapshot({"known": key("known")}, {"known": "provider"})

    with patch.object(service.requests, "get", side_effect=requests.Timeout) as fetch:
        # Advance the clock and the cooldown together so the stale age alone decides the outcome.
        fresh_now = 100.0 + service.MAX_PINNED_JWKS_STALE_SECONDS - 1
        monkeypatch.setattr(time, "monotonic", Mock(return_value=fresh_now))
        service._last_jwks_refresh_time = fresh_now
        assert service.get_jwk(token("known")).key_id == "known"

        expired_now = 100.0 + service.MAX_PINNED_JWKS_STALE_SECONDS
        monkeypatch.setattr(time, "monotonic", Mock(return_value=expired_now))
        service._last_jwks_refresh_time = expired_now
        with pytest.raises(service.ClueKeyError):
            service.get_jwk(token("known"))
    fetch.assert_not_called()


def test_partial_provider_failure_keeps_revocation_and_other_pinned_keys(service, monkeypatch):
    monkeypatch.setattr(
        service.config.auth.oauth,
        "providers",
        {
            "provider-a": SimpleNamespace(jwks_uri="https://idp-a/jwks"),
            "provider-b": SimpleNamespace(jwks_uri="https://idp-b/jwks"),
        },
    )
    service._pinned_jwks = snapshot(
        {"key-a": key("key-a"), "key-b": key("key-b")},
        {"key-a": "provider-a", "key-b": "provider-b"},
    )

    def fetch_keys(uri, timeout):
        if uri == "https://idp-a/jwks":
            return Mock(json=lambda: {"keys": []})
        raise requests.Timeout

    with patch.object(service.requests, "get", side_effect=fetch_keys) as fetch:
        with pytest.raises(service.ClueKeyError):
            service.get_jwk(token("key-a"))
        assert service.get_jwk(token("key-b")).key_id == "key-b"
        assert service.get_provider(token("key-b")) == "provider-b"

        # Provider A's revocation stays in effect after the cache entry is evicted.
        service.cache.delete("get_jwks")
        with pytest.raises(service.ClueKeyError):
            service.get_jwk(token("key-a"))
        assert service.get_jwk(token("key-b")).key_id == "key-b"
    assert fetch.call_count == 2


def test_refresh_result_filters_stale_carried_over_keys_post_fetch(service, monkeypatch):
    monkeypatch.setattr(
        service.config.auth.oauth,
        "providers",
        {
            "provider-a": SimpleNamespace(jwks_uri="https://idp-a/jwks"),
            "provider-b": SimpleNamespace(jwks_uri="https://idp-b/jwks"),
        },
    )
    limit = service.MAX_PINNED_JWKS_STALE_SECONDS
    service._pinned_jwks = snapshot({"key-b": key("key-b")}, {"key-b": "provider-b"}, fetched_at=100.0)
    clock = Mock(return_value=100.0 + limit - 1)  # provider B's key is 1 second from expiring
    monkeypatch.setattr(time, "monotonic", clock)

    def fetch_keys(uri, timeout):
        if uri == "https://idp-a/jwks":
            return Mock(json=lambda: {"keys": [key("key-a")]})
        clock.return_value += 2  # the slow failing request pushes B's key past the limit
        raise requests.Timeout

    with patch.object(service.requests, "get", side_effect=fetch_keys):
        jwks, providers = service.get_jwks(refresh=True)

    assert list(jwks) == ["key-a"]
    assert providers == {"key-a": "provider-a"}
    assert list(service._pinned_jwks.jwks) == ["key-a"]
    assert list(service.cache.get("get_jwks").jwks) == ["key-a"]
    assert "provider-b" not in service._pinned_jwks.timestamps


def test_keys_kept_through_a_partial_failure_still_expire(service, monkeypatch):
    monkeypatch.setattr(
        service.config.auth.oauth,
        "providers",
        {
            "provider-a": SimpleNamespace(jwks_uri="https://idp-a/jwks"),
            "provider-b": SimpleNamespace(jwks_uri="https://idp-b/jwks"),
        },
    )
    service._pinned_jwks = snapshot({"key-b": key("key-b")}, {"key-b": "provider-b"})

    def fetch_keys(uri, timeout):
        if uri == "https://idp-a/jwks":
            return Mock(json=lambda: {"keys": [key("key-a")]})
        raise requests.Timeout

    with patch.object(service.requests, "get", side_effect=fetch_keys):
        # Provider A keeps succeeding, but provider B's keys keep their original age.
        expired_now = 100.0 + service.MAX_PINNED_JWKS_STALE_SECONDS
        monkeypatch.setattr(time, "monotonic", Mock(return_value=expired_now - 1))
        assert service.get_jwk(token("key-b")).key_id == "key-b"
        service.cache.delete("get_jwks")
        service._last_jwks_refresh_time = None
        monkeypatch.setattr(time, "monotonic", Mock(return_value=expired_now))
        assert service.get_jwk(token("key-a")).key_id == "key-a"
        with pytest.raises(service.ClueKeyError):
            service.get_jwk(token("key-b"))


@pytest.mark.parametrize(
    "payload",
    [{"keys": None}, {"keys": "oops"}, [], ["key"], None, "text", {"other": []}],
)
def test_malformed_payload_falls_back_to_unexpired_pinned_keys(service, payload):
    service._pinned_jwks = snapshot({"known": key("known")}, {"known": "provider"})
    with patch.object(service.requests, "get", return_value=Mock(json=lambda: payload)) as fetch:
        assert service.decode(token("known"), algorithms=["HS256"]) == {"sub": "user"}
    assert fetch.call_count == 1


def test_malformed_payload_without_pinned_keys_propagates(service):
    with patch.object(service.requests, "get", return_value=Mock(json=lambda: {"keys": None})):
        with pytest.raises(ValueError, match="Malformed JWKS"):
            service.get_jwk(token("known"))


def test_malformed_key_entries_are_ignored(service):
    keys = [None, "text", 1, {}, {"kid": None}, {"kid": 5}, {"kid": ""}, {"kid": "no-kty"}, key("good")]
    with patch.object(service.requests, "get", return_value=Mock(json=lambda: {"keys": keys})):
        assert service.get_jwk(token("good")).key_id == "good"
    assert list(service.cache.get("get_jwks").jwks) == ["good"]


def test_max_pinned_stale_age_is_twelve_hours():
    assert jwt_service.MAX_PINNED_JWKS_STALE_SECONDS == 43200


@pytest.mark.parametrize(
    "bad_key",
    [
        {"kid": "known"},
        {"kid": "known", "kty": 5},
        {"kid": "known", "kty": "RSA"},
        {"kid": "known", "kty": "oct", "alg": "HS256"},
        {"kid": "known", "kty": "unsupported", "k": "dGVzdC1zZWNyZXQ"},
    ],
)
def test_malformed_crypto_key_does_not_overwrite_pinned_key(service, bad_key):
    pinned = snapshot({"known": key("known")}, {"known": "provider"})
    service._pinned_jwks = pinned
    with patch.object(service.requests, "get", return_value=Mock(json=lambda: {"keys": [bad_key]})) as fetch:
        assert service.decode(token("known"), algorithms=["HS256"]) == {"sub": "user"}
    assert fetch.call_count == 1
    assert service._pinned_jwks == pinned
    assert service.cache.get("get_jwks") is None


def test_malformed_crypto_key_alongside_valid_keys_is_ignored(service):
    keys = [{"kid": "broken"}, key("good")]
    with patch.object(service.requests, "get", return_value=Mock(json=lambda: {"keys": keys})):
        assert service.get_jwk(token("good")).key_id == "good"
        with pytest.raises(service.ClueKeyError):
            service.get_jwk(token("broken"))
    assert list(service._pinned_jwks.jwks) == ["good"]


def test_cache_hit_does_not_serve_keys_older_than_max_stale_age(service, monkeypatch):
    monkeypatch.setattr(
        service.config.auth.oauth,
        "providers",
        {
            "provider-a": SimpleNamespace(jwks_uri="https://idp-a/jwks"),
            "provider-b": SimpleNamespace(jwks_uri="https://idp-b/jwks"),
        },
    )
    limit = service.MAX_PINNED_JWKS_STALE_SECONDS
    service._pinned_jwks = snapshot(
        {"key-a": key("key-a"), "key-b": key("key-b")},
        {"key-a": "provider-a", "key-b": "provider-b"},
    )

    def fetch_keys(uri, timeout):
        if uri == "https://idp-a/jwks":
            return Mock(json=lambda: {"keys": [key("key-a")]})
        raise requests.Timeout

    # A partial refresh just before the limit re-caches provider B's old key with its original age.
    just_before = 100.0 + limit - 10
    monkeypatch.setattr(time, "monotonic", Mock(return_value=just_before))
    with patch.object(service.requests, "get", side_effect=fetch_keys) as fetch:
        service.get_jwks()
        assert set(service.cache.get("get_jwks").jwks) == {"key-a", "key-b"}
        assert service.decode(token("key-b"), algorithms=["HS256"]) == {"sub": "user"}

        # Past the limit the cache is left untouched, but provider B's key must no longer verify.
        monkeypatch.setattr(time, "monotonic", Mock(return_value=100.0 + limit))
        assert set(service.cache.get("get_jwks").jwks) == {"key-a", "key-b"}
        with pytest.raises(service.ClueKeyError):
            service.decode(token("key-b"), algorithms=["HS256"])
        with pytest.raises(service.ClueValueError):
            service.get_provider(token("key-b"))
        assert service.decode(token("key-a"), algorithms=["HS256"]) == {"sub": "user"}
    assert fetch.call_count == 2


@pytest.mark.parametrize(
    "failure",
    [
        requests.Timeout,
        requests.ConnectionError,
        ValueError,
        KeyError,
        lambda: Mock(json=lambda: {"unexpected": []}),
        lambda: Mock(raise_for_status=Mock(side_effect=requests.HTTPError)),
    ],
)
def test_fetch_failure_falls_back_to_unexpired_pinned_keys(service, failure):
    service._pinned_jwks = snapshot({"known": key("known")}, {"known": "provider"})
    assert service.cache.get("get_jwks") is None
    effect = failure if isinstance(failure, type) else None
    value = None if effect else failure()
    with patch.object(service.requests, "get", side_effect=effect, return_value=value) as fetch:
        assert service.decode(token("known"), algorithms=["HS256"]) == {"sub": "user"}
        with pytest.raises(service.ClueKeyError):
            service.get_jwk(token("unknown"))
    assert fetch.call_count == 1
    assert service.cache.get("get_jwks") is None


def test_fetch_failure_with_expired_pinned_keys_propagates(service, monkeypatch):
    service._pinned_jwks = snapshot({"known": key("known")}, {"known": "provider"})
    monkeypatch.setattr(time, "monotonic", Mock(return_value=100.0 + service.MAX_PINNED_JWKS_STALE_SECONDS))
    with patch.object(service.requests, "get", side_effect=requests.Timeout):
        with pytest.raises(requests.Timeout):
            service.get_jwk(token("known"))


def test_fallback_snapshot_retains_authoritative_empty_keys_with_mixed_expired_provider(service, monkeypatch):
    monkeypatch.setattr(
        service.config.auth.oauth,
        "providers",
        {
            "provider-a": SimpleNamespace(jwks_uri="https://idp-a/jwks"),
            "provider-b": SimpleNamespace(jwks_uri="https://idp-b/jwks"),
        },
    )
    expired_at = 100.0 - service.MAX_PINNED_JWKS_STALE_SECONDS - 1
    service._pinned_jwks = JWKSSnapshot(
        {"key-b": key("key-b")},
        {"key-b": "provider-b"},
        {"provider-a": 100.0, "provider-b": expired_at},
    )

    fallback = service._unexpired_pinned_jwks()
    assert fallback is not None
    assert set(fallback.timestamps) == {"provider-a"}
    assert fallback.jwks == {}

    # All providers failing serves the authoritative empty snapshot instead of propagating the error.
    with patch.object(service.requests, "get", side_effect=requests.Timeout):
        jwks, providers = service.get_jwks(refresh=True)
    assert jwks == {}
    assert providers == {}
    with pytest.raises(service.ClueKeyError):
        service.get_jwk(token("key-b"))


def test_fallback_keys_never_overwrite_a_fresh_cache_entry(service, monkeypatch):
    service._pinned_jwks = snapshot({"old": key("old")}, {"old": "provider"})
    started = Event()
    release = Event()

    def fetch_keys(*args, **kwargs):
        started.set()
        assert release.wait(timeout=5)
        return Mock(json=lambda: {"keys": [key("new")]})

    with (
        patch.object(service.requests, "get", side_effect=fetch_keys),
        ThreadPoolExecutor(max_workers=1) as pool,
    ):
        # Thread A refreshes; thread B is served fallback keys while A holds the lock.
        thread_a = pool.submit(_in_app, service, service.get_jwks, True)
        assert started.wait(timeout=5)
        with patch.object(service.cache, "set") as fallback_set:
            fallback_jwks, _ = service.get_jwks()
        fallback_set.assert_not_called()
        assert "old" in fallback_jwks
        release.set()
        fresh_jwks, _ = thread_a.result(timeout=5)

        # B resolves again after A finished and the cooldown is active; the cache must keep A's keys.
        service.get_jwks()
        service.get_jwks(refresh=True)
    assert list(fresh_jwks) == ["new"]
    assert list(service.cache.get("get_jwks").jwks) == ["new"]


def test_snapshot_timestamp_concurrency_race(service, monkeypatch):
    limit = service.MAX_PINNED_JWKS_STALE_SECONDS
    old_snapshot = snapshot({"old": key("old")}, {"old": "provider"}, fetched_at=0.0)
    service._pinned_jwks = old_snapshot
    service.cache.set("get_jwks", old_snapshot, timeout=43200)
    monkeypatch.setattr(time, "monotonic", Mock(return_value=limit + 1))

    reached = Event()
    resume = Event()
    evaluated = []
    real_fresh_only = service._fresh_only

    def paused_fresh_only(snap, now=None):
        if current_thread().name.startswith("thread-a"):
            evaluated.append(snap)
            reached.set()
            assert resume.wait(timeout=5)
        return real_fresh_only(snap, now)

    monkeypatch.setattr(service, "_fresh_only", paused_fresh_only)

    with (
        patch.object(service.requests, "get", return_value=Mock(json=lambda: {"keys": [key("new")]})),
        ThreadPoolExecutor(max_workers=1, thread_name_prefix="thread-a") as pool,
    ):
        # Thread A reads the old snapshot from the cache and stops right before checking freshness.
        thread_a = pool.submit(_in_app, service, service.get_jwks)
        assert reached.wait(timeout=5)

        # Thread B refreshes past the 12 hour limit, replacing the cache entry and the pinned snapshot.
        fresh_jwks, _ = service.get_jwks(refresh=True)
        assert list(fresh_jwks) == ["new"]
        assert service._pinned_jwks.timestamps == {"provider": limit + 1}
        assert service.cache.get("get_jwks").timestamps == {"provider": limit + 1}

        resume.set()
        stale_jwks, stale_providers = thread_a.result(timeout=5)

    # A judged its snapshot by that snapshot's own T=0 timestamps, not by B's newer ones.
    assert evaluated == [old_snapshot]
    assert evaluated[0].timestamps == {"provider": 0.0}
    assert stale_jwks == {}
    assert stale_providers == {}


def test_fresh_only_uses_only_the_snapshot_timestamps(service, monkeypatch):
    limit = service.MAX_PINNED_JWKS_STALE_SECONDS
    stale = snapshot({"old": key("old")}, {"old": "provider"}, fetched_at=0.0)
    monkeypatch.setattr(service, "_pinned_jwks", snapshot({"new": key("new")}, {"new": "provider"}, fetched_at=500.0))

    assert service._fresh_only(stale, now=limit) == JWKSSnapshot({}, {}, {})
    assert list(service._fresh_only(stale, now=limit - 1).jwks) == ["old"]
    # A provider missing from the snapshot's timestamps is never considered fresh.
    no_timestamps = JWKSSnapshot({"old": key("old")}, {"old": "provider"}, {})
    assert service._fresh_only(no_timestamps, now=1.0).jwks == {}


def test_cooldown_configuration_defaults_to_sixty_seconds():
    assert OAuth().jwks_refresh_cooldown_seconds == 60


@pytest.mark.parametrize("seconds", [0, -1])
def test_cooldown_configuration_rejects_nonpositive_values(seconds):
    with pytest.raises(ValidationError):
        OAuth(jwks_refresh_cooldown_seconds=seconds)


def test_extract_audience():
    access_token = get_token()

    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    assert "clue" in extract_audience(access_token)
