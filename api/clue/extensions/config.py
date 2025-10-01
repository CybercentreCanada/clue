import logging
from typing import Any

from pydantic import BaseModel, ImportString, model_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    YamlConfigSettingsSource,
)

from clue.common.logging import CLUE_DATE_FORMAT, CLUE_LOG_FORMAT

logger = logging.getLogger("clue.extensions.config")
logger.setLevel(logging.INFO)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
console.setFormatter(logging.Formatter(CLUE_LOG_FORMAT, CLUE_DATE_FORMAT))
logger.addHandler(console)


class Modules(BaseModel):
    "A list of components exposed for use in Clue by this plugin."

    routes: list[ImportString] = []
    obo_module: ImportString | None = None


class BaseExtensionConfig(BaseSettings):
    "Configuration File for Plugin"

    name: str
    features: dict[str, bool] = {}

    modules: Modules = Modules()

    @model_validator(mode="before")
    @classmethod
    def initialize_extension_configuration(cls, data: Any) -> Any:  # noqa: C901
        "Convert a raw yaml config into an object ready for validation by pydantic"
        if not isinstance(data, dict):
            return data

        # Default mutation requires plugin name
        if "name" not in data:
            logger.warning("Name is missing from configuration")
            return data

        plugin_name = data["name"]
        logger.debug("Beginning configuration parsing for plugin %s", plugin_name)

        if "modules" not in data:
            return data

        if "routes" in data["modules"] and isinstance(data["modules"]["routes"], list):
            new_routes: list[str] = []
            for route in data["modules"]["routes"]:
                new_routes.append(f"{plugin_name}.routes.{route}" if "." not in route else route)

            data["modules"]["routes"] = new_routes

        if "obo_module" in data["modules"]:
            if isinstance(data["modules"]["obo_module"], bool):
                data["modules"]["obo_module"] = f"{plugin_name}.obo:get_obo_token"

        return data

    @classmethod
    def settings_customise_sources(
        cls,  # noqa: ANN102
        *args,  # noqa: ANN002
        **kwargs,  # noqa: ANN002, ANN102
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        "Adds a YamlConfigSettingsSource object at the end of the settings_customize_sources response."
        return (*super().settings_customise_sources(*args, **kwargs), YamlConfigSettingsSource(cls))
