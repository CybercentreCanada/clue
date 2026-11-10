from unittest.mock import patch

from flask import Flask

from clue.constants.supported_types import SUPPORTED_TYPES
from clue.models.config import ExternalSource
from clue.services import type_service


def test_detection_metadata_keeps_registry_order_and_v1_regex_response():
    user = {"classification": "TLP:CLEAR"}
    discovered = {
        "source": {
            "ja3": "TLP:CLEAR",
            "domain": "TLP:RED",
            "md5": "TLP:CLEAR",
            "ipv4": "TLP:CLEAR",
        }
    }
    with (
        patch.object(type_service, "all_supported_types", return_value=discovered),
        patch.object(type_service.CLASSIFICATION, "is_accessible", side_effect=lambda _, c: c == "TLP:CLEAR"),
    ):
        metadata = type_service.get_types_detection(user)
        legacy = type_service.get_types_regular_expressions(user)

    assert list(metadata) == ["ipv4", "md5", "ja3"]
    assert metadata == {key: SUPPORTED_TYPES[key] for key in ["ipv4", "md5", "ja3"]}
    assert all(metadata[key] is not SUPPORTED_TYPES[key] for key in metadata)
    assert list(legacy) == ["ja3", "md5", "ipv4"]
    assert legacy == {key: SUPPORTED_TYPES[key]["regex"] for key in legacy}


def test_v2_endpoint_preserves_registry_order_on_the_wire():
    import inspect

    from clue.api.v1.lookup import get_types_detection as get_legacy_detection
    from clue.api.v1.lookup import lookup_api as legacy_api
    from clue.api.v2.lookup import get_types_detection, lookup_api

    app = Flask(__name__)
    app.json.sort_keys = True
    app.register_blueprint(lookup_api)
    app.register_blueprint(legacy_api)
    metadata = {key: SUPPORTED_TYPES[key] for key in ["ipv4", "md5", "ja3"]}
    with (
        app.test_request_context("/api/v2/lookup/types_detection/"),
        patch.object(type_service, "get_types_detection", return_value=metadata),
    ):
        response = inspect.unwrap(get_types_detection)(user={"classification": "TLP:CLEAR"})

    assert list(response.get_json()["api_response"]) == ["ipv4", "md5", "ja3"]
    assert response.status_code == 200
    assert any(rule.rule == "/api/v2/lookup/types_detection/" for rule in app.url_map.iter_rules())

    legacy = {key: metadata[key]["regex"] for key in metadata}
    with (
        app.test_request_context("/api/v1/lookup/types_detection/"),
        patch.object(type_service, "get_types_regular_expressions", return_value=legacy),
    ):
        response = inspect.unwrap(get_legacy_detection)(user={"classification": "TLP:CLEAR"})
    assert response.get_json()["api_response"] == legacy
    assert list(response.get_json()["api_response"]) == sorted(legacy)


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
