import re
from unittest.mock import patch

import pytest
from flask import Flask

from clue.api.v1.lookup import lookup_api as lookup_v1_api
from clue.api.v2.lookup import lookup_api as lookup_v2_api
from clue.constants.supported_types import SUPPORTED_TYPES
from clue.models.auth_user import AuthResult, AuthUser, Privilege
from clue.models.selector import Selector


@pytest.fixture
def app():
    app = Flask(__name__)
    app.register_blueprint(lookup_v1_api)
    app.register_blueprint(lookup_v2_api)
    return app


@pytest.mark.parametrize("version", [1, 2])
def test_detection_requires_authentication(app, version):
    response = app.test_client().get(f"/api/v{version}/lookup/types_detection/")
    assert response.status_code == 401


def test_v1_and_v2_payloads_and_serialized_registry_order(app):
    auth = AuthResult(user=AuthUser(uname="test", classification="TLP:CLEAR"), privileges={Privilege.READ})
    source_types = {
        "plugin": {
            "ja3": "TLP:CLEAR",
            "md5": "TLP:CLEAR",
            "domain": "TLP:CLEAR",
            "ip": "TLP:CLEAR",
            "ipv6": "TLP:CLEAR",
        }
    }
    with (
        patch("clue.security.auth_service.bearer_auth", return_value=auth),
        patch("clue.services.type_service.all_supported_types", return_value=source_types),
    ):
        client = app.test_client()
        v1 = client.get("/api/v1/lookup/types_detection/", headers={"Authorization": "Bearer test"})
        v2 = client.get("/api/v2/lookup/types_detection/", headers={"Authorization": "Bearer test"})

    assert v1.status_code == v2.status_code == 200
    assert v1.json["api_response"] == {key: SUPPORTED_TYPES[key]["regex"] for key in source_types["plugin"]}
    metadata = v2.json["api_response"]
    assert list(metadata) == ["ipv6", "ip", "domain", "md5", "ja3"]
    assert metadata["ipv6"]["priority"] == 10
    assert metadata["ip"]["regex"] is None
    assert metadata["domain"]["case_sensitive"] is False
    assert "priority" not in metadata["md5"]
    assert v2.json["api_status_code"] == 200


@pytest.mark.parametrize(
    "type_name,value",
    [
        ("email_address", "Alice@EXAMPLE.COM"),
        ("email_address", "Alice@SubDomain.Example.COM"),
        ("ipv6", "::FFFF:192.0.2.1"),
        ("ipv6", "FE80::1%eth0"),
        ("url", "http://[::FFFF:192.0.2.1]/MixedCase"),
        ("url", "http://[FE80::1%eth0]/MixedCase"),
    ],
)
def test_builtin_metadata_accepts_case_variants_without_normalizing_selectors(app, type_name, value):
    auth = AuthResult(user=AuthUser(uname="test", classification="TLP:CLEAR"), privileges={Privilege.READ})
    with (
        patch("clue.security.auth_service.bearer_auth", return_value=auth),
        patch("clue.services.type_service.all_supported_types", return_value={"plugin": {type_name: "TLP:CLEAR"}}),
    ):
        response = app.test_client().get("/api/v2/lookup/types_detection/", headers={"Authorization": "Bearer test"})

    assert response.status_code == 200
    metadata = response.json["api_response"][type_name]
    assert metadata["case_sensitive"] is True
    assert re.fullmatch(metadata["regex"], value)
    assert Selector(type=type_name, value=value).value == value
