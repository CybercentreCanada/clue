# This file contains the loaders for the different components of the system
from __future__ import annotations

import logging
import os
from pathlib import Path
from string import Template
from typing import TYPE_CHECKING

from flask_caching import Cache

from clue.common.dict_utils import recursive_update
from clue.common.logging.format import CLUE_DATE_FORMAT, CLUE_LOG_FORMAT
from clue.common.str_utils import default_string_value

APP_NAME: str = default_string_value(env_name="APP_NAME", default="clue")  # type: ignore[assignment]
APP_PREFIX = os.environ.get("APP_PREFIX", "brl")

if TYPE_CHECKING:
    from clue.common.classification import Classification

cache = Cache(config={"CACHE_TYPE": "SimpleCache"})

classification_engines: dict[Path, Classification] = {}

logger = logging.getLogger(f"{APP_NAME}.common.forge")
logger.setLevel(logging.INFO)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
console.setFormatter(logging.Formatter(CLUE_LOG_FORMAT, CLUE_DATE_FORMAT))
logger.addHandler(console)


def __get_yml_path(yml_config: str | None = None) -> Path | None:  # noqa: C901
    if yml_config is not None:
        return Path(yml_config)

    if (_yml_path := Path(f"/etc/{APP_NAME}/classification.yml")).exists():
        return _yml_path

    if (_yml_path := Path(f"/etc/{APP_NAME}/conf/classification.yml")).exists():
        return _yml_path

    if os.getenv("AZURE_TEST_CONFIG", None) is not None:
        import re

        logger.info("Azure build environment detected, checking additional classification path")

        work_dir_parent = Path("/__w")
        work_dir: Path | None = None
        for sub_path in work_dir_parent.iterdir():
            if not sub_path.is_dir():
                continue

            logger.info("Testing sub path %s", sub_path)

            if re.match(r"\d+", sub_path.name):
                work_dir = work_dir_parent / sub_path

            if work_dir is not None:
                logger.info("Subpath %s exists, checking for test path", work_dir)
                test_classification_path = work_dir / "s" / "test" / "config" / "classification.yml"

                if test_classification_path.exists():
                    logger.info("Path %s detected", test_classification_path)
                    return test_classification_path

                logger.error("No classification path found at path %s", test_classification_path)
                logger.info(
                    "Available files:\n%s", "\n".join(sorted(str(path) for path in (work_dir / "s").glob("**/*")))
                )
                work_dir = None

    custom_path = os.environ.get("CLUE_CONF_FOLDER", None)
    if custom_path is None:
        return None

    if (_yml_path := (Path(custom_path) / "classification.yml")).exists():
        return _yml_path

    return None


def get_classification(yml_config: str | None = None):  # noqa: C901
    """Creates and registers a Classification engine.

    If a yaml config is not provided, it will search in /etc/clue and /etc/clue/conf for a classification.yml
    file instead.

    Arguments:
        yml_config: An optional yaml config to load.

    Returns:
        The created Classification engine.
    """
    import yaml

    from clue.common.classification import Classification, InvalidDefinition

    _yml_path = __get_yml_path(yml_config)

    if _yml_path:
        logger.debug("Classification file found at %s", _yml_path)
    else:
        logger.warning("Missing classification.yml file!")

    if _yml_path in classification_engines:
        return classification_engines[_yml_path]

    classification_definition = {}
    default_file = Path(__file__).parent / "classification.yml"
    if default_file.exists():
        with default_file.open() as default_fh:
            default_yml_data = yaml.safe_load(default_fh.read())
            if default_yml_data:
                classification_definition.update(default_yml_data)

    # Load modifiers from the yaml config
    if _yml_path is not None and _yml_path.exists():
        with _yml_path.open() as yml_fh:
            yml_data = yaml.safe_load(yml_fh.read())
            if yml_data:
                classification_definition = recursive_update(classification_definition, yml_data)

    if not classification_definition:
        raise InvalidDefinition("Could not find any classification definition to load.")

    classification_engine = Classification(classification_definition)

    if _yml_path:
        classification_engines[_yml_path] = classification_engine

    return classification_engine


def env_substitute(buffer):
    """Replace environment variables in the buffer with their value.

    Use the built in template expansion tool that expands environment variable style strings ${}
    We set the idpattern to none so that $abc doesn't get replaced but ${abc} does.

    Case insensitive.
    Variables that are found in the buffer, but are not defined as environment variables are ignored.
    """
    return Template(buffer).safe_substitute(os.environ, idpattern=None, bracedidpattern="(?a:[_a-z][_a-z0-9]*)")


def get_metrics_sink(redis=None):
    """Creates a clue_metrics CommsQueue on redis for metrics."""
    from clue.remote.datatypes.queues.comms import CommsQueue

    return CommsQueue("clue_metrics", host=redis)
