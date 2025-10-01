import logging
from pathlib import Path
from typing import cast

import pytest
from pydantic_settings import SettingsConfigDict

from clue.app import app
from clue.extensions.config import BaseExtensionConfig
from clue.models.config import OBOService
from clue.security.obo import get_obo_token


class ClueTextExtensionConfig(BaseExtensionConfig):
    model_config = SettingsConfigDict(
        yaml_file=Path(__file__).parent / "test-extension.yml", yaml_file_encoding="utf-8", strict=True
    )


def mock_get_token(service: str, access_token: str, user: str):
    from clue.extensions import _config

    if _config.api.obo_targets[service].scope == "extension_obo_scope":
        return "access_token"

    raise ValueError("Only other_service is supported")


@pytest.fixture(autouse=True, scope="module")
def mock_plugin():
    from clue.extensions import EXTENSIONS

    conf = ClueTextExtensionConfig(name="test-extension")

    EXTENSIONS["test-extension"] = conf

    yield EXTENSIONS["test-extension"]

    del EXTENSIONS["test-extension"]


def test_auth_hooks(caplog):
    with app.test_request_context():
        from clue.extensions import EXTENSIONS, _config

        _config.api.obo_targets["other_service"] = OBOService(enabled=True, scope="extension_obo_scope", quota=None)

        with caplog.at_level(logging.INFO):
            assert get_obo_token("other_service", "bad_token", "user", force_refresh=True) == "bad_token"

        assert "No OBO function provided, returning provided access token" in caplog.text

        caplog.clear()

        cast(BaseExtensionConfig, EXTENSIONS["test-extension"]).modules.obo_module = mock_get_token

        with caplog.at_level(logging.INFO):
            assert get_obo_token("other_service", "bad_token", "user", force_refresh=True) == "access_token"

        assert "No OBO function provided, returning provided access token" not in caplog.text

        _config.api.obo_targets["unsupported_service"] = OBOService(
            enabled=True, scope="unsupported_obo_scope", quota=None
        )

        with caplog.at_level(logging.INFO):
            assert get_obo_token("unsupported_service", "bad_token", "user", force_refresh=True) is None

        assert "Exception on OBO:" in caplog.text

        del _config.api.obo_targets["unsupported_service"]
        del _config.api.obo_targets["other_service"]
