from unittest.mock import patch

from flask import Flask

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
