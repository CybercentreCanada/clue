import logging
from datetime import datetime

import pytest
from pydantic_core import Url

from clue.cache import Cache
from clue.models.network import Annotation, QueryEntry
from clue.plugin import CluePlugin
from clue.plugin.utils import Params


@pytest.fixture(scope="module")
def mock_plugin() -> CluePlugin:
    plugin = CluePlugin(
        app_name="tester",
        classification="TLP:CLEAR",
        supported_types={"ipv4", "ipv6"},
        enrich=lambda *args: QueryEntry(count=10, annotations=[], link=Url("https://example.com")),
        logger=logging.getLogger("test"),
    )

    return plugin


def test_cache_local(mock_plugin: CluePlugin):
    cache = Cache("testing-cache", mock_plugin.app, "local", timeout=60)

    test_data = [
        QueryEntry(count=6, annotations=[]),
        QueryEntry(
            count=3,
            annotations=[
                Annotation(
                    analytic="test analytic",
                    type="opinion",
                    value="malicious",
                    confidence=0.8,
                    summary="test",
                    timestamp=datetime.now(),
                )
            ],
        ),
    ]

    with mock_plugin.app.test_request_context():
        params = Params.from_request()

        cache.set(
            "ip",
            "127.0.0.1",
            params,
            test_data,
        )

        assert cache.get("ip", "127.0.0.1", params) == test_data


def test_cache_redis(mock_plugin: CluePlugin):
    cache = Cache("testing-cache", mock_plugin.app, "redis", timeout=60)

    test_data = [
        QueryEntry(count=6, annotations=[]),
        QueryEntry(
            count=3,
            annotations=[
                Annotation(
                    analytic="test analytic",
                    type="opinion",
                    value="malicious",
                    confidence=0.8,
                    summary="test",
                    timestamp=datetime.now(),
                )
            ],
        ),
    ]

    with mock_plugin.app.test_request_context():
        params = Params.from_request()

        cache.set(
            "ip",
            "127.0.0.1",
            params,
            test_data,
        )

        assert cache.get("ip", "127.0.0.1", params) == test_data
