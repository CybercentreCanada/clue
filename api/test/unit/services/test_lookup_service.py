from unittest.mock import Mock, patch

import pytest
from flask import Flask

from clue.config import config
from clue.models.auth_user import AuthResult, AuthUser, Privilege
from clue.models.config import ExternalSource
from clue.models.network import QueryEntry, QueryResult
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


@pytest.fixture
def classified_result():
    return {
        "type": "ipv4",
        "value": "127.0.0.1",
        "source": "test",
        "items": [
            {"classification": "TLP:CLEAR"},
            {"classification": "TLP:GREEN"},
            {"classification": "TLP:AMBER+STRICT"},
        ],
    }


def test_query_result_filters_items_by_user_classification(classified_result):
    result = QueryResult.model_validate(classified_result, context={"user": {"classification": "TLP:GREEN"}})

    assert [item.classification for item in result.items] == ["TLP:CLEAR", "TLP:GREEN"]


@pytest.mark.parametrize(
    "context",
    [
        None,
        {},
        {"other": True},
        {"user": None},
        {"user": {}},
        {"user": {"classification": None}},
        {"user": {"classification": ""}},
        "invalid",
        ["user"],
        {"user": "invalid"},
        {"user": ["invalid"]},
        {"user": {"classification": 123}},
        {"user": {"classification": True}},
        {"user": {"classification": ["TLP:GREEN"]}},
        {"user": {"classification": {"level": "TLP:GREEN"}}},
        {"user": {"classification": "NOT_A_CLASSIFICATION"}},
        {"user": {"classification": "TLP:GREEN//UNKNOWN"}},
        {"user": {"classification": "TLP:GREEN//"}},
        {"user": {"classification": "INVALID"}},
        {"user": {"classification": "inv"}},
        {"user": {"classification": "INVALID//"}},
    ],
)
def test_query_result_without_user_classification_fails_closed(classified_result, context):
    result = QueryResult.model_validate(classified_result, context=context)

    assert result.items == []


def test_query_result_direct_construction_fails_closed(classified_result):
    assert QueryResult(**classified_result).items == []


@pytest.mark.parametrize(
    ("clearance", "expected"),
    [
        ("TLP:CLEAR", []),
        ("TLP:GREEN", ["TLP:GREEN"]),
        ("TLP:AMBER+STRICT", ["TLP:GREEN"]),
    ],
)
def test_query_result_clearance_boundaries(classified_result, clearance, expected):
    classified_result["items"] = [{"classification": "TLP:GREEN"}]

    result = QueryResult.model_validate(classified_result, context={"user": {"classification": clearance}})

    assert [item.classification for item in result.items] == expected


def test_query_result_item_assignment_without_context_fails_closed(classified_result):
    result = QueryResult.model_validate(classified_result, context={"user": {"classification": "TLP:GREEN"}})

    result.items = result.items

    assert result.items == []


@pytest.mark.parametrize("production", [False, True])
def test_parse_bulk_response_filters_items_by_user_classification(source, classified_result, production):
    source.production = production
    result = lookup_service.parse_bulk_response(
        source,
        {"classification": "TLP:GREEN"},
        {"ipv4": {"127.0.0.1": classified_result}},
    )["ipv4"]["127.0.0.1"]

    assert [item.classification for item in result.items] == ["TLP:CLEAR", "TLP:GREEN"]


@pytest.mark.parametrize("bulk", [False, True])
def test_production_response_bypasses_validation(source, user, bulk):
    source.production = True
    items = [{"classification": "TLP:CLEAR", "count": "not-an-integer"}]

    if bulk:
        result = lookup_service.parse_bulk_response(source, user, {"ipv4": {"127.0.0.1": {"items": items}}})["ipv4"][
            "127.0.0.1"
        ]
        assert result.items[0].classification == "TLP:CLEAR"
        assert result.items[0].count == "not-an-integer"
    else:
        result_items = lookup_service.parse_response(source, user, items)
        assert result_items[0].classification == "TLP:CLEAR"
        assert result_items[0].count == "not-an-integer"


@pytest.mark.parametrize("bulk", [False, True])
@pytest.mark.parametrize(
    "classification", [None, "", 123, True, [], {}, "NOT_A_CLASSIFICATION", "INV", "INVALID", "TLP:AMBER+STRICT"]
)
def test_production_response_rejects_invalid_or_inaccessible_classification(source, user, bulk, classification, caplog):
    source.production = True
    items = [
        {"classification": "TLP:CLEAR"},
        {"classification": classification, "raw_data": "RESTRICTED_TEST_MARKER"},
        {"raw_data": "RESTRICTED_TEST_MARKER"},
    ]

    if bulk:
        result = lookup_service.parse_bulk_response(source, user, {"ipv4": {"127.0.0.1": {"items": items}}})["ipv4"][
            "127.0.0.1"
        ]
    else:
        result = lookup_service.build_result(
            "ipv4", "127.0.0.1", source, user=user, items=lookup_service.parse_response(source, user, items)
        )

    assert [item.classification for item in result.items] == ["TLP:CLEAR"]
    assert "RESTRICTED_TEST_MARKER" not in result.model_dump_json()
    assert "RESTRICTED_TEST_MARKER" not in caplog.text


@pytest.mark.parametrize("classification", [None, "", 123, "INVALID", "NOT_A_CLASSIFICATION"])
def test_query_result_rejects_unvalidated_item_classification(classified_result, user, classification):
    classified_result["items"] = [
        QueryEntry.model_construct(classification=classification, raw_data="RESTRICTED_TEST_MARKER")
    ]

    result = QueryResult.model_validate(classified_result, context={"user": user})

    assert result.items == []
    assert "RESTRICTED_TEST_MARKER" not in result.model_dump_json()


@pytest.mark.parametrize("bulk", [False, True])
@pytest.mark.parametrize("user", [None, {}, {"classification": "INVALID"}, {"classification": "NOT_A_CLASSIFICATION"}])
def test_production_response_requires_valid_user_classification(source, user, bulk):
    source.production = True
    items = [{"classification": "TLP:CLEAR", "raw_data": "RESTRICTED_TEST_MARKER"}]

    if bulk:
        result = lookup_service.parse_bulk_response(source, user, {"ipv4": {"127.0.0.1": {"items": items}}})["ipv4"][
            "127.0.0.1"
        ]
        assert result.items == []
        assert "RESTRICTED_TEST_MARKER" not in result.model_dump_json()
    else:
        assert lookup_service.parse_response(source, user, items) == []


@pytest.mark.parametrize("production", [False, True])
def test_query_external_filters_items_by_user_classification(app, source, classified_result, production):
    source.production = production
    response = Mock(status_code=200)
    response.json.return_value = {"api_response": classified_result["items"]}
    client = Mock()
    client.get.return_value = response

    with (
        app.test_request_context(),
        patch.object(config.api, "audit", False),
        patch(
            "clue.services.lookup_service.type_service.get_supported_types",
            return_value={"ipv4": "TLP:CLEAR"},
        ),
        patch("clue.services.lookup_service.user_service.check_quota", return_value=None),
        patch("clue.services.lookup_service.user_service.release_quota"),
        patch("clue.services.lookup_service.generate_headers", return_value={}),
        patch("clue.services.lookup_service.get_client", return_value=client),
    ):
        result = lookup_service.query_external(
            {"classification": "TLP:GREEN"}, source, "ipv4", "127.0.0.1", 10, 2.0, "token", None
        )

    assert result is not None
    assert result.error is None
    assert [item.classification for item in result.items] == ["TLP:CLEAR", "TLP:GREEN"]


@pytest.mark.parametrize("bulk", [False, True])
def test_cwe_696_lookup_validation_errors_do_not_disclose_restricted_items(app, source, user, bulk, caplog):
    """Prevent disclosure when nested validation runs before classification filtering."""
    source.production = False
    restricted_marker = "RESTRICTED_TEST_MARKER"
    items = [
        {
            "classification": "TLP:AMBER+STRICT",
            "annotations": [
                {
                    "analytic": "test",
                    "type": "opinion",
                    "value": restricted_marker,
                    "confidence": 1.0,
                    "summary": "test",
                }
            ],
        }
    ]
    response = Mock(status_code=200)
    response.json.return_value = {"api_response": {"ipv4": {"127.0.0.1": {"items": items}}} if bulk else items}
    client = Mock()
    client.get.return_value = response
    client.post.return_value = response

    with (
        app.test_request_context(),
        patch.object(config.api, "audit", False),
        patch(
            "clue.services.lookup_service.type_service.get_supported_types",
            return_value={"ipv4": "TLP:CLEAR"},
        ),
        patch("clue.services.lookup_service.user_service.check_quota", return_value=None),
        patch("clue.services.lookup_service.user_service.release_quota"),
        patch("clue.services.lookup_service.generate_headers", return_value={}),
        patch("clue.services.lookup_service.get_client", return_value=client),
    ):
        if bulk:
            result = lookup_service.bulk_query_external(
                [Selector(type="ipv4", value="127.0.0.1")], user, source, 10, 2.0, "token", None
            )["ipv4"]["127.0.0.1"]
        else:
            result = lookup_service.query_external(user, source, "ipv4", "127.0.0.1", 10, 2.0, "token", None)

    assert result is not None
    assert result.items == []
    assert result.error.startswith("test returned an improperly formatted response. Error ID: ")
    assert restricted_marker not in result.model_dump_json()
    assert restricted_marker not in caplog.text
    assert "assertion_error" in caplog.text
    assert "annotations" in caplog.text
    assert all(record.exc_info is None for record in caplog.records)


@pytest.mark.parametrize("production", [False, True])
@pytest.mark.parametrize("bulk", [False, True])
def test_lookup_route_passes_authenticated_user_context(app, source, classified_result, production, bulk):
    from clue.api.v1.lookup import lookup_api

    app.register_blueprint(lookup_api)
    source.production = production
    auth_result = AuthResult(
        user=AuthUser(uname="test-user", classification="TLP:GREEN"),
        privileges={Privilege.READ, Privilege.WRITE},
    )
    response = Mock(status_code=200)
    response.json.return_value = {
        "api_response": {"ipv4": {"127.0.0.1": classified_result}} if bulk else classified_result["items"]
    }
    client = Mock()
    client.get.return_value = response
    client.post.return_value = response

    with (
        patch("clue.security.auth_service.bearer_auth", return_value=auth_result),
        patch.object(config.api, "audit", False),
        patch.object(config.ui, "replication", False),
        patch("clue.services.lookup_service.get_sources", return_value=[source]),
        patch("clue.services.lookup_service.get_obo_access_token", return_value=("test-token", None)),
        patch(
            "clue.services.lookup_service.type_service.get_supported_types",
            return_value={"ipv4": "TLP:CLEAR"},
        ),
        patch("clue.services.lookup_service.user_service.check_quota", return_value=None),
        patch("clue.services.lookup_service.user_service.release_quota"),
        patch("clue.services.lookup_service.generate_headers", return_value={}),
        patch("clue.services.lookup_service.get_client", return_value=client),
        app.test_client() as api_client,
    ):
        headers = {"Authorization": "Bearer test-token"}
        if bulk:
            api_response = api_client.post(
                "/api/v1/lookup/enrich?sources=test",
                headers=headers,
                json=[{"type": "ipv4", "value": "127.0.0.1"}],
            )
        else:
            api_response = api_client.get("/api/v1/lookup/enrich/ipv4/127.0.0.1/?sources=test", headers=headers)

    assert api_response.status_code == 200
    results = api_response.get_json()["api_response"]
    result = results["ipv4"]["127.0.0.1"]["test"] if bulk else results["test"]
    assert not result.get("error")
    assert [item["classification"] for item in result["items"]] == ["TLP:CLEAR", "TLP:GREEN"]


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
            "clue.services.lookup_service.type_service.get_supported_types",
            return_value={"ipv4": "TLP:CLEAR"},
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
            "clue.services.lookup_service.type_service.get_supported_types",
            return_value={"ipv4": "TLP:CLEAR"},
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
        patch("clue.services.lookup_service.get_obo_access_token", return_value=("access-token", None)),
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
        patch("clue.services.lookup_service.get_obo_access_token", return_value=("access-token", None)),
        patch("clue.services.lookup_service.bulk_query_external", return_value={}),
        patch("clue.services.lookup_service.mongo_service.invalidate_existing") as invalidate_existing,
        patch("clue.services.lookup_service.mongo_service.existing_results", return_value={}) as existing_results,
    ):
        lookup_service.bulk_enrich([selector], user)

    existing_results.assert_called_once_with("test-user", "selectors", [selector], [source])
    invalidate_existing.assert_not_called()
