from unittest.mock import patch

import pytest
from flask import Flask
from pydantic import ValidationError

from clue.api.v1.registration import register_application, remove_application
from clue.cronjobs.plugins import update_external_source_list
from clue.models.auth_user import Privilege, UserRole
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
        mock_config.api.registration_allowed_origins = ["http://plugin"]
        update_external_source_list()

        assert mock_config.api.external_sources == [built_in]


@pytest.mark.parametrize(
    "url",
    ["http://plugins.example:8443/lookup", "https://plugins.example/lookup", "https://attacker.example/lookup"],
)
def test_runtime_source_requires_an_allowed_exact_origin(url):
    context = {"registration_allowed_origins": ["https://plugins.example:8443"]}

    with pytest.raises(ValidationError, match="External source URL origin is not permitted"):
        ExternalSource.model_validate({"name": "test", "url": url, "built_in": False}, context=context)

    assert (
        ExternalSource.model_validate(
            {"name": "test", "url": "https://plugins.example:8443/lookup", "built_in": False}, context=context
        ).name
        == "test"
    )


def test_runtime_source_rejects_credentialed_urls():
    with pytest.raises(ValidationError, match="External source URL origin is not permitted"):
        ExternalSource.model_validate(
            {"name": "test", "url": "https://user:password@plugins.example/", "built_in": False},
            context={"registration_allowed_origins": ["https://plugins.example"]},
        )


def test_runtime_source_is_disabled_without_allowed_origins():
    with pytest.raises(ValidationError, match="External source URL origin is not permitted"):
        ExternalSource(name="test", url="https://plugins.example/", built_in=False)


def test_runtime_source_rejects_an_existing_source_name():
    with pytest.raises(ValidationError, match="An external source with that name already exists"):
        ExternalSource.model_validate(
            {"name": "built-in", "url": "https://plugins.example/", "built_in": False},
            context={
                "registration_allowed_origins": ["https://plugins.example"],
                "existing_source_names": {"built-in"},
            },
        )


def test_built_in_source_skips_runtime_origin_and_name_checks():
    source = ExternalSource.model_validate(
        {"name": "built-in", "url": "https://plugins.example/", "built_in": True},
        context={"registration_allowed_origins": [], "existing_source_names": {"built-in"}},
    )

    assert source.name == "built-in"


def test_plugin_refresh_ignores_disallowed_and_duplicate_runtime_sources():
    built_in = ExternalSource(name="built-in", url="https://plugins.example/")
    entries = [
        {"name": "disallowed", "url": "https://other.example/"},
        {"name": "built-in", "url": "https://plugins.example/"},
        {"name": "approved", "url": "https://plugins.example/"},
        {"name": "approved", "url": "https://plugins.example/"},
    ]
    with (
        patch("clue.cronjobs.plugins.config") as mock_config,
        patch("clue.cronjobs.plugins.EXTERNAL_PLUGIN_SET.members", return_value=entries),
    ):
        mock_config.api.external_sources = [built_in]
        mock_config.api.registration_allowed_origins = ["https://plugins.example"]
        update_external_source_list()

    assert [source.name for source in mock_config.api.external_sources] == ["built-in", "approved"]


def test_registration_handler_rejects_disallowed_origin():
    app = Flask(__name__)
    payload = {"name": "attacker", "url": "http://attacker.example/"}

    with (
        app.test_request_context("/register/", method="POST", json=payload),
        patch("clue.api.v1.registration.config") as mock_config,
        patch("clue.api.v1.registration.EXTERNAL_PLUGIN_SET.members", return_value=[]),
        patch("clue.api.v1.registration.EXTERNAL_PLUGIN_SET.add") as add_plugin,
    ):
        mock_config.api.registration_allowed_origins = ["https://plugins.example"]
        mock_config.api.external_sources = []
        handler = getattr(getattr(register_application, "__wrapped__"), "__wrapped__")
        response = handler()

    assert response.status_code == 400
    assert response.json["api_error_message"] == "External source URL origin is not permitted for runtime registration"
    assert mock_config.api.external_sources == []
    add_plugin.assert_not_called()


def test_registration_handler_returns_invalid_url_error():
    app = Flask(__name__)
    with (
        app.test_request_context("/register/", method="POST", json={"name": "bad", "url": "file:///etc/passwd"}),
        patch("clue.api.v1.registration.config") as mock_config,
        patch("clue.api.v1.registration.EXTERNAL_PLUGIN_SET.members", return_value=[]),
        patch("clue.api.v1.registration.EXTERNAL_PLUGIN_SET.add") as add_plugin,
    ):
        mock_config.api.registration_allowed_origins = ["https://plugins.example"]
        mock_config.api.external_sources = []
        handler = getattr(getattr(register_application, "__wrapped__"), "__wrapped__")
        response = handler()

    assert response.status_code == 400
    assert "URL scheme should be 'http' or 'https'" in response.json["api_error_message"]
    add_plugin.assert_not_called()


def test_registration_handler_persists_allowlisted_source():
    app = Flask(__name__)
    payload = {"name": "approved", "url": "https://plugins.example/"}

    with (
        app.test_request_context("/register/", method="POST", json=payload),
        patch("clue.api.v1.registration.config") as mock_config,
        patch("clue.api.v1.registration.EXTERNAL_PLUGIN_SET.members", return_value=[]),
        patch("clue.api.v1.registration.EXTERNAL_PLUGIN_SET.add") as add_plugin,
    ):
        mock_config.api.registration_allowed_origins = ["https://plugins.example"]
        mock_config.api.external_sources = []
        handler = getattr(getattr(register_application, "__wrapped__"), "__wrapped__")
        response = handler()

    assert response.status_code == 200
    assert [source.name for source in mock_config.api.external_sources] == ["approved"]
    add_plugin.assert_called_once_with(mock_config.api.external_sources[0].model_dump(mode="json", exclude_none=True))


def test_registration_handler_forces_runtime_source_to_not_built_in():
    app = Flask(__name__)
    payload = {"name": "approved", "url": "https://plugins.example/", "built_in": True}

    with (
        app.test_request_context("/register/", method="POST", json=payload),
        patch("clue.api.v1.registration.config") as mock_config,
        patch("clue.api.v1.registration.EXTERNAL_PLUGIN_SET.members", return_value=[]),
        patch("clue.api.v1.registration.EXTERNAL_PLUGIN_SET.add") as add_plugin,
    ):
        mock_config.api.registration_allowed_origins = ["https://plugins.example"]
        mock_config.api.external_sources = []
        handler = getattr(getattr(register_application, "__wrapped__"), "__wrapped__")
        response = handler()

    assert response.status_code == 200
    assert mock_config.api.external_sources[0].built_in is False
    assert add_plugin.call_args.args[0]["built_in"] is False


def test_registration_handler_rejects_duplicate_without_mutation():
    app = Flask(__name__)
    existing = ExternalSource(name="existing", url="https://plugins.example/")
    payload = {"name": "existing", "url": "https://plugins.example/"}

    with (
        app.test_request_context("/register/", method="POST", json=payload),
        patch("clue.api.v1.registration.config") as mock_config,
        patch("clue.api.v1.registration.EXTERNAL_PLUGIN_SET.members", return_value=[]),
        patch("clue.api.v1.registration.EXTERNAL_PLUGIN_SET.add") as add_plugin,
    ):
        mock_config.api.registration_allowed_origins = ["https://plugins.example"]
        mock_config.api.external_sources = [existing]
        handler = getattr(getattr(register_application, "__wrapped__"), "__wrapped__")
        response = handler()

    assert response.status_code == 400
    assert response.json["api_error_message"] == "An external source with that name already exists"
    assert mock_config.api.external_sources == [existing]
    add_plugin.assert_not_called()


def test_registration_handler_rejects_persisted_duplicate_without_mutation():
    app = Flask(__name__)
    payload = {"name": "persisted", "url": "https://plugins.example/"}
    persisted = {"name": "persisted", "url": "https://plugins.example/", "built_in": False}

    with (
        app.test_request_context("/register/", method="POST", json=payload),
        patch("clue.api.v1.registration.config") as mock_config,
        patch("clue.api.v1.registration.EXTERNAL_PLUGIN_SET.members", return_value=[persisted]),
        patch("clue.api.v1.registration.EXTERNAL_PLUGIN_SET.add") as add_plugin,
    ):
        mock_config.api.registration_allowed_origins = ["https://plugins.example"]
        mock_config.api.external_sources = []
        handler = getattr(getattr(register_application, "__wrapped__"), "__wrapped__")
        response = handler()

    assert response.status_code == 400
    assert response.json["api_error_message"] == "An external source with that name already exists"
    assert mock_config.api.external_sources == []
    add_plugin.assert_not_called()
