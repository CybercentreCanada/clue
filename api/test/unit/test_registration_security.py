from unittest.mock import patch

import pytest
from pydantic import ValidationError

from clue.api.v1.registration import (
    is_registration_name_available,
    is_registration_url_allowed,
    register_application,
    remove_application,
)
from clue.cronjobs.plugins import update_external_source_list
from clue.models.auth import Privilege, UserRole
from clue.models.config import ExternalSource


@pytest.mark.parametrize("url", ["file:///etc/passwd", "gopher://127.0.0.1/", "not-a-url"])
def test_external_source_rejects_non_http_urls(url: str):
    with pytest.raises(ValidationError):
        ExternalSource(name="invalid", url=url)


def test_registration_routes_require_admin_write_access():
    for endpoint in (register_application, remove_application):
        assert getattr(endpoint, "required_roles") == [UserRole.ADMIN]
        assert getattr(endpoint, "required_priv") == [Privilege.WRITE]


def test_plugin_refresh_ignores_legacy_invalid_runtime_source():
    built_in = ExternalSource(name="built-in", url="http://plugin/")

    with (
        patch("clue.cronjobs.plugins.config") as mock_config,
        patch(
            "clue.cronjobs.plugins.EXTERNAL_PLUGIN_SET.members",
            return_value=[{"name": "invalid", "url": "file:///etc/passwd", "built_in": False}],
        ),
    ):
        mock_config.api.external_sources = [built_in]
        update_external_source_list()

        assert mock_config.api.external_sources == [built_in]


def test_runtime_registration_requires_an_allowed_exact_origin():
    with patch("clue.api.v1.registration.config") as mock_config:
        mock_config.api.registration_allowed_origins = ["https://plugins.example:8443"]

        assert is_registration_url_allowed("https://plugins.example:8443/lookup")
        assert not is_registration_url_allowed("http://plugins.example:8443/lookup")
        assert not is_registration_url_allowed("https://plugins.example/lookup")
        assert not is_registration_url_allowed("https://attacker.example/lookup")


def test_runtime_registration_rejects_credentialed_and_malformed_urls():
    with patch("clue.api.v1.registration.config") as mock_config:
        mock_config.api.registration_allowed_origins = ["https://plugins.example"]

        assert not is_registration_url_allowed("https://user:password@plugins.example/")
        assert not is_registration_url_allowed("file:///etc/passwd")
        assert not is_registration_url_allowed("not-a-url")


def test_runtime_registration_is_disabled_without_allowed_origins():
    with patch("clue.api.v1.registration.config") as mock_config:
        mock_config.api.registration_allowed_origins = []

        assert not is_registration_url_allowed("https://plugins.example/")


def test_runtime_registration_rejects_an_existing_source_name():
    with patch("clue.api.v1.registration.config") as mock_config:
        mock_config.api.external_sources = [ExternalSource(name="built-in", url="http://plugin/")]

        assert not is_registration_name_available("built-in")
        assert is_registration_name_available("new-plugin")
