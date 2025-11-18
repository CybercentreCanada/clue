import logging
from pathlib import Path

from pydantic_settings import SettingsConfigDict

from clue.extensions import BaseExtensionConfig


class HowlerTestPluginConfig(BaseExtensionConfig):
    model_config = SettingsConfigDict(
        yaml_file=Path(__file__).parent / "test-extension.yml", yaml_file_encoding="utf-8", strict=True
    )


def test_get_plugins(caplog):
    from clue.extensions import _config, get_extensions

    assert len(get_extensions()) == 0

    _config.core.extensions.add("no-existy")

    with caplog.at_level(logging.ERROR):
        assert len(get_extensions()) == 0

    assert "Exception when loading extension no-existy" in caplog.text

    from clue.extensions import EXTENSIONS

    assert "no-existy" in EXTENSIONS

    _config.core.extensions.add("test-extension")

    EXTENSIONS["test-extension"] = HowlerTestPluginConfig(name="test-extension")

    assert len(get_extensions()) == 1

    del EXTENSIONS["test-extension"]

    _config.core.extensions.remove("no-existy")
    _config.core.extensions.remove("test-extension")
