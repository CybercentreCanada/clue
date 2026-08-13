from unittest.mock import patch

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
def user():
    return {"uname": "test-user", "classification": "TLP:CLEAR"}


def test_bulk_enrich_invalidates_cached_results_when_no_cache(app, source, user):
    selector = Selector(type="ipv4", value="127.0.0.1")

    with (
        app.test_request_context("/?no_cache=true", headers={"Authorization": "Bearer access-token"}),
        patch.object(config.ui, "replication", True),
        patch("clue.services.lookup_service.get_sources", return_value=[source]),
        patch("clue.services.lookup_service.mongo_service.invalidate_existing") as invalidate_existing,
        patch("clue.services.lookup_service.mongo_service.existing_results") as existing_results,
    ):
        lookup_service.bulk_enrich([selector], user)

    invalidate_existing.assert_called_once_with("test-user", "selectors", [selector], [source])
    existing_results.assert_not_called()


def test_bulk_enrich_reuses_cached_results_when_cache_is_enabled(app, source, user):
    selector = Selector(type="ipv4", value="127.0.0.1")

    with (
        app.test_request_context("/", headers={"Authorization": "Bearer access-token"}),
        patch.object(config.ui, "replication", True),
        patch("clue.services.lookup_service.get_sources", return_value=[source]),
        patch("clue.services.lookup_service.mongo_service.invalidate_existing") as invalidate_existing,
        patch("clue.services.lookup_service.mongo_service.existing_results", return_value={}) as existing_results,
    ):
        lookup_service.bulk_enrich([selector], user)

    existing_results.assert_called_once_with("test-user", "selectors", [selector], [source])
    invalidate_existing.assert_not_called()
