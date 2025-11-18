import importlib
import logging
from pathlib import Path

import pytest
import werkzeug
from pydantic_settings import SettingsConfigDict

from clue.extensions.config import BaseExtensionConfig

# Workaround: Some tests or Flask extensions expect werkzeug.__version__ to be set to a valid string.
# In certain environments, this attribute may be missing or incorrect, causing import or compatibility errors.
# Setting it explicitly ensures consistent behavior during testing.
werkzeug.__version__ = "1.0.0"  # type: ignore


class ClueTestExtensionConfig(BaseExtensionConfig):
    model_config = SettingsConfigDict(
        yaml_file=Path(__file__).parent / "test-extension.yml", yaml_file_encoding="utf-8", strict=True
    )


@pytest.fixture(autouse=True, scope="module")
def mock_plugin():
    from clue.extensions import EXTENSIONS

    conf = ClueTestExtensionConfig(name="test-extension")

    EXTENSIONS["test-extension"] = conf

    yield EXTENSIONS

    del EXTENSIONS["test-extension"]


def test_route_hook(caplog):
    with caplog.at_level(logging.INFO):
        app = importlib.import_module("clue.app")
        importlib.reload(app)

    assert "Enabling additional endpoint: /api/v1/test" not in caplog.text

    from clue.extensions import EXTENSIONS

    EXTENSIONS["test-extension"].modules.routes.append(
        importlib.import_module("test.utils.extensions.example_route").example_route
    )  # type: ignore[union-attr]

    with caplog.at_level(logging.INFO):
        app = importlib.import_module("clue.app")
        importlib.reload(app)

    assert "Enabling additional endpoint: /api/v1/test" in caplog.text

    client = app.app.test_client()
    assert client.get("/api/v1/test/example").json["api_response"] == {"success": True}
