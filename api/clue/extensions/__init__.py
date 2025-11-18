import importlib
from typing import Optional

from clue.common.logging import get_logger
from clue.config import config as _config  # Python gets BIG mad if we don't alias this
from clue.extensions.config import BaseExtensionConfig

logger = get_logger(__file__)

EXTENSIONS: dict[str, Optional[BaseExtensionConfig]] = {}


def get_extensions() -> list[BaseExtensionConfig]:
    "Get a set of extension configurations based on the clue settings."
    for extension in _config.core.extensions:
        if extension in EXTENSIONS:
            continue

        logger.info("Initializing extension %s", extension)
        try:
            EXTENSIONS[extension] = importlib.import_module(f"{extension}.config").config
        except (ImportError, ModuleNotFoundError):
            logger.exception("Exception when loading extension %s", extension)
            EXTENSIONS[extension] = None

    return [extension for extension in EXTENSIONS.values() if extension]
