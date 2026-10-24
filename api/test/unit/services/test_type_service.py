from unittest.mock import patch

import pytest
from flask import Flask

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
