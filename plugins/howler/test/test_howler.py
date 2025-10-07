import base64
import json
from datetime import datetime

import pytest
from clue.models.network import Annotation
from clue.models.selector import Selector
from clue.plugin import CluePlugin
from pydantic_core import Url


@pytest.fixture(scope="module")
def howler():
    from app import plugin  # type: ignore

    return plugin


def test_validate_token(howler: CluePlugin):
    jwt_data = json.dumps(
        {
            "aud": "7fd79813-310c-456f-b90e-2fdbdf55471b",
        }
    )

    token = f"xx.{base64.b64encode(jwt_data.encode()).decode()}"

    with howler.app.test_request_context(headers={"Authorization": f"Bearer {token}"}):
        from app import validate_token

        result = validate_token()

        assert result[0] == token

    jwt_data = json.dumps(
        {
            "aud": "other audience",
        }
    )

    token = f"xx.{base64.b64encode(jwt_data.encode()).decode()}"

    with howler.app.test_request_context(headers={"Authorization": f"Bearer {token}"}):
        from app import validate_token

        result = validate_token()

        assert "expected audience" in result[1]


def test_rebuild_link():
    from app import update_annotation

    annotation = Annotation(
        analytic="test",
        type="assessment",
        value="development",
        confidence=0.0,
        summary="test",
        link=Url("https://howler.example.com/hits/test1"),
    )

    update_annotation(annotation, "test2")

    assert annotation.link is not None

    assert annotation.link.path == "/search"
    assert annotation.link.query_params() == [("span", "date.range.all"), ("query", "howler.id:(test1 OR test2)")]

    update_annotation(annotation, "test3")

    assert annotation.link is not None

    assert annotation.link.path == "/search"
    assert annotation.link.query_params() == [
        ("span", "date.range.all"),
        ("query", "howler.id:(test1 OR test2 OR test3)"),
    ]


def test_pivot(howler: CluePlugin):
    pivot = howler.actions[0]

    from app import SearchPivotRequest

    assert howler.run_action is not None

    result = howler.run_action(pivot, SearchPivotRequest(selector=Selector(type="ip", value="127.0.0.1")), "potato")
    expected = Url(
        'https://howler.example.com/search?query=(howler.outline.threat:"127.0.0.1" OR '
        'howler.outline.target:"127.0.0.1" OR destination.address:"127.0.0.1" OR destination.ip:"127.0.0.1" '
        'OR destination.nat.ip:"127.0.0.1" OR dns.resolved_ip:"127.0.0.1" OR email.parent.destination:"127.0.0.1" '
        'OR email.parent.source:"127.0.0.1" OR host.ip:"127.0.0.1" OR related.ip:"127.0.0.1" OR '
        'server.address:"127.0.0.1" OR server.ip:"127.0.0.1" OR source.address:"127.0.0.1" OR source.ip:"127.0.0.1"'
        ' OR source.nat.ip:"127.0.0.1" OR threat.indicator.ip:"127.0.0.1")'
    ).query

    assert expected is not None
    assert result.output is not None and result.output.query is not None

    for i in range(len(expected)):
        assert result.output.query[i] == expected[i], f"Character at column {i} does not match"

    start_date = datetime(year=2025, month=1, day=1).isoformat()
    end_date = datetime(year=2025, month=1, day=2).isoformat()

    result = howler.run_action(
        pivot,
        SearchPivotRequest(
            selector=Selector(type="ip", value="127.0.0.1"),
            start_date=start_date,
            end_date=end_date,
        ),
        "potato",
    )
    expected = Url(
        'https://howler.example.com/search?query=(howler.outline.threat:"127.0.0.1" OR '
        'howler.outline.target:"127.0.0.1" OR destination.address:"127.0.0.1" OR destination.ip:"127.0.0.1" '
        'OR destination.nat.ip:"127.0.0.1" OR dns.resolved_ip:"127.0.0.1" OR email.parent.destination:"127.0.0.1" '
        'OR email.parent.source:"127.0.0.1" OR host.ip:"127.0.0.1" OR related.ip:"127.0.0.1" OR '
        'server.address:"127.0.0.1" OR server.ip:"127.0.0.1" OR source.address:"127.0.0.1" OR source.ip:"127.0.0.1"'
        ' OR source.nat.ip:"127.0.0.1" OR threat.indicator.ip:"127.0.0.1")'
        f"&span=date.range.custom&start_date={start_date}&end_date={end_date}"
    ).query

    assert expected is not None
    assert result.output is not None and result.output.query is not None

    for i in range(len(expected)):
        assert result.output.query[i] == expected[i], f"Character at column {i} does not match"
