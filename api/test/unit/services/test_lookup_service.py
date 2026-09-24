from unittest.mock import Mock, patch

import pytest
from flask import Flask

from clue.config import config
from clue.models.config import ExternalSource
from clue.models.selector import Selector
from clue.services import lookup_service


@pytest.fixture
def app():
    return Flask(__name__)


@pytest.fixture
def source():
    return ExternalSource(name="test", url="http://plugin/", include_default=False)


@pytest.fixture
def excluded_source():
    return ExternalSource(name="excluded", url="http://excluded/", include_default=True)


@pytest.fixture
def user():
    return {"uname": "test-user", "classification": "TLP:CLEAR"}


@pytest.mark.parametrize("base_url", ["http://plugin", "http://plugin/", "http://plugin/api/"])
def test_query_external_uses_single_slash_after_base_url(base_url, app, user):
    source = ExternalSource(name="test", url=base_url)
    response = Mock(status_code=200)
    response.json.return_value = {"api_response": []}
    client = Mock()
    client.get.return_value = response

    with (
        app.test_request_context(),
        patch.object(config.api, "audit", False),
        patch(
            "clue.services.lookup_service.type_service.all_supported_types",
            return_value={"test": {"ipv4": "TLP:CLEAR"}},
        ),
        patch("clue.services.lookup_service.user_service.check_quota", return_value=None),
        patch("clue.services.lookup_service.user_service.release_quota"),
        patch("clue.services.lookup_service.generate_headers", return_value={}),
        patch("clue.services.lookup_service.get_client", return_value=client),
    ):
        lookup_service.query_external(user, source, "ipv4", "127.0.0.1", 10, 2.0, "token", None)

    expected = f"{source.url.rstrip('/')}/lookup/ipv4/127.0.0.1/"
    client.get.assert_called_once()
    assert client.get.call_args.args[0] == expected


@pytest.mark.parametrize("base_url", ["http://plugin", "http://plugin/", "http://plugin/api/"])
def test_bulk_query_external_uses_single_slash_after_base_url(base_url, app, user):
    source = ExternalSource(name="test", url=base_url)
    response = Mock(status_code=200)
    response.json.return_value = {"api_response": []}
    client = Mock()
    client.post.return_value = response
    selector = Selector(type="ipv4", value="127.0.0.1")

    with (
        app.test_request_context(),
        patch.object(config.api, "audit", False),
        patch(
            "clue.services.lookup_service.type_service.all_supported_types",
            return_value={"test": {"ipv4": "TLP:CLEAR"}},
        ),
        patch("clue.services.lookup_service.user_service.check_quota", return_value=None),
        patch("clue.services.lookup_service.generate_headers", return_value={}),
        patch("clue.services.lookup_service.get_client", return_value=client),
    ):
        lookup_service.bulk_query_external([selector], user, source, 10, 2.0, "token", None)

    client.post.assert_called_once()
    assert client.post.call_args.args[0] == f"{source.url.rstrip('/')}/lookup/"


def test_bulk_enrich_invalidates_only_requested_cached_results_when_no_cache(app, source, excluded_source, user):
    selector = Selector(type="ipv4", value="127.0.0.1")

    with (
        app.test_request_context(
            "/?sources=test,-excluded&no_cache=true", headers={"Authorization": "Bearer access-token"}
        ),
        patch.object(config.ui, "replication", True),
        patch("clue.services.lookup_service.get_sources", return_value=[source, excluded_source]),
        patch("clue.services.lookup_service.auth_service.check_obo", return_value=(None, None)),
        patch("clue.services.lookup_service.bulk_query_external", return_value={}),
        patch("clue.services.lookup_service.mongo_service.invalidate_existing") as invalidate_existing,
        patch("clue.services.lookup_service.mongo_service.existing_results") as existing_results,
    ):
        lookup_service.bulk_enrich([selector], user)

    invalidate_existing.assert_called_once_with("test-user", "selectors", [selector], [source])
    existing_results.assert_not_called()


def test_bulk_enrich_reuses_only_requested_cached_results_when_cache_is_enabled(app, source, excluded_source, user):
    selector = Selector(type="ipv4", value="127.0.0.1")

    with (
        app.test_request_context("/?sources=test,-excluded", headers={"Authorization": "Bearer access-token"}),
        patch.object(config.ui, "replication", True),
        patch("clue.services.lookup_service.get_sources", return_value=[source, excluded_source]),
        patch("clue.services.lookup_service.auth_service.check_obo", return_value=(None, None)),
        patch("clue.services.lookup_service.bulk_query_external", return_value={}),
        patch("clue.services.lookup_service.mongo_service.invalidate_existing") as invalidate_existing,
        patch("clue.services.lookup_service.mongo_service.existing_results", return_value={}) as existing_results,
    ):
        lookup_service.bulk_enrich([selector], user)

    existing_results.assert_called_once_with("test-user", "selectors", [selector], [source])
    invalidate_existing.assert_not_called()
