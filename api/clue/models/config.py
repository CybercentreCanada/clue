# ruff: noqa: D101
import logging
import os
from email.utils import parseaddr
from enum import Enum
from pathlib import Path
from typing import Self
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import Url
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

from clue.common import forge
from clue.common.exceptions import ClueValueError
from clue.common.logging.format import CLUE_DATE_FORMAT, CLUE_LOG_FORMAT
from clue.common.str_utils import default_string_value

AUTO_PROPERTY_TYPE = ["access", "classification", "type", "role", "remove_role", "group"]
DEFAULT_EMAIL_FIELDS = ["email", "emails", "extension_selectedEmailAddress", "otherMails", "preferred_username", "upn"]
DEFAULT_USER_FIELDS = ["uname", "preferred_username", "upn"]
DEFAULT_USER_NAME_FIELDS = ["name", "displayName"]
APP_NAME = default_string_value(env_name="APP_NAME", default="clue").replace("-dev", "")  # type: ignore[union-attr]
CLASSIFICATION = forge.get_classification()


class PasswordRequirement(BaseModel):
    lower: bool = Field(description="Password must contain lowercase letters", default=False)
    number: bool = Field(description="Password must contain numbers", default=False)
    special: bool = Field(description="Password must contain special characters", default=False)
    upper: bool = Field(description="Password must contain uppercase letters", default=False)
    min_length: int = Field(description="Minimum password length", default=12)


class OAuthProvider(BaseModel):
    auto_create: bool = Field(default=True, description="Auto-create users if they are missing")
    auto_sync: bool = Field(default=False, description="Should we automatically sync with OAuth provider?")
    uid_randomize: bool = Field(
        default=False,
        description="Should we generate a random username for the authenticated user?",
    )
    uid_randomize_digits: int = Field(
        default=0,
        description="How many digits should we add at the end of the username?",
    )
    uid_randomize_delimiter: str = Field(
        default="-",
        description="What is the delimiter used by the random name generator?",
    )
    uid_regex: str | None = Field(
        description="Regex used to parse an email address and capture parts to create a user ID out of it", default=None
    )
    uid_format: str | None = Field(
        description="Format of the user ID based on the captured parts from the regex", default=None
    )
    client_id: str | None = Field(description="ID of your application to authenticate to the OAuth provider")
    client_secret: str | None = Field(
        description="Password to your application to authenticate to the OAuth provider", default=None
    )
    required_groups: list[str] = Field(
        default=[], description="The groups the JWT must contain in order to allow access"
    )
    role_map: dict[str, str] = Field(default={}, description="A mapping of OAuth groups to clue roles")
    classification_map: dict[str, str] = Field(
        default={}, description="A mapping of OAuth groups to classification levels"
    )
    access_token_url: str = Field(description="URL to get access token")
    authorize_url: str | None = Field(description="URL used to authorize access to a resource")
    api_base_url: str | None = Field(description="Base URL for downloading the user's and groups info")
    audience: str | None = Field(
        description="The audience to validate against. Only must be set if audience is different than the client id."
    )
    scope: str = Field(description="The scope to validate against")
    iss: str | None = Field(description="Optional issuer field for JWT validation", default=None)
    jwks_uri: str = Field(description="URL used to verify if a returned JWKS token is valid")


class OAuth(BaseModel):
    enabled: bool = Field(description="Enable use of OAuth?", default=False)
    gravatar_enabled: bool = Field(description="Enable gravatar?", default=False)
    providers: dict[str, OAuthProvider] = Field(default={}, description="OAuth provider configuration")
    other_audiences: list[str] | None = Field(
        default=None, description="What other audiences in JWT tokens should Clue accept?"
    )

    @model_validator(mode="before")
    @classmethod
    def prepare_model(
        cls,  # noqa: ANN102
        oauth_data: dict[str, dict[str, dict | OAuthProvider]],  # noqa: ANN102
    ) -> dict[str, dict[str, dict | OAuthProvider]]:
        """Validates the oauth data, and adds the client secret if it's not already there.

        Args:
            oauth_data (dict[str, dict[str, dict | OAuthProvider]]): The data to validate.

        Returns:
            dict[str, dict[str, dict | OAuthProvider]]: The validated data with the client secrets.
        """
        if "providers" in oauth_data and isinstance(oauth_data["providers"], dict):
            for name, provider in oauth_data["providers"].items():
                if isinstance(provider, OAuthProvider):
                    provider.client_secret = default_string_value(
                        provider.client_secret,
                        env_name=f"{name.upper()}_CLIENT_SECRET",
                    )
                elif isinstance(provider, dict):
                    provider["client_secret"] = default_string_value(
                        provider.get("client_secret", None),
                        env_name=f"{name.upper()}_CLIENT_SECRET",
                    )

        return oauth_data


class ServiceAccountCreds(BaseModel):
    username: str = Field(description="Username of the service account")
    password: str = Field(description="Password of the service account")
    provider: str = Field(description="What OAuth provider does this service account connect to?")

    @model_validator(mode="before")
    @classmethod
    def prepare_model(cls, data: dict[str, str]) -> dict[str, str]:  # noqa: ANN102
        """Adds the service account password to the data if missing.

        Args:
            data (dict[str, str]): The data to validate.

        Returns:
            dict[str, str]: The data including the password.
        """
        if "password" not in data and "provider" in data:
            if env_pass := os.getenv(f'SA_{data["provider"].upper()}_PASSWORD'):
                data["password"] = env_pass

        return data


class ServiceAccount(BaseModel):
    enabled: bool = Field(description="Enable use of a service account?", default=False)
    accounts: list[ServiceAccountCreds] = Field(
        description="A list of service accounts on a per-provider basis", default=[]
    )

    @model_validator(mode="after")
    def validate_model(self: Self) -> Self:
        """Validates the model.

        Raises:
            ClueValueError: Raised whenever there is more than one service account per provider.

        Returns:
            Self: The validated model.
        """
        providers = {account.provider for account in self.accounts}

        if len(providers) != len(self.accounts):
            raise ClueValueError("You may only have one service account per provider.")

        return self


class Auth(BaseModel):
    allow_apikeys: bool = Field(description="Allow API keys?", default=False)
    apikeys: dict[str, str] = Field(default={}, description="API Keys available in the system")
    propagate_clue_key: bool = Field(
        default=True, description="Should clue include the root clue token in requests when OBO is used?"
    )
    oauth: OAuth = OAuth()
    service_account: ServiceAccount = ServiceAccount()

    @model_validator(mode="after")
    def validate_model(self: Self) -> Self:
        """Validates the model.

        Raises:
            ClueValueError: Raised whenever there is an invalid value in the model.

        Returns:
            Self: The validated model.
        """
        if not self.service_account.enabled:
            return self

        if not self.oauth.enabled:
            raise ClueValueError("In order to use service accounts to connect to plugins, you must have oauth enabled.")

        for account in self.service_account.accounts:
            if account.provider not in self.oauth.providers:
                raise ClueValueError(
                    f"{account.username} is used to connect to non-existent provider {account.provider}."
                )

        return self


class RedisServer(BaseModel):
    host: str = Field(description="Hostname of Redis instance", default="127.0.0.1")
    port: int = Field(description="Port of Redis instance", default=6379)
    password: str | None = Field(description="Password to connect to redis", default=None)


class APMServer(BaseModel):
    server_url: str | None = Field(description="URL to API server", default=None)
    token: str | None = Field(description="Authentication token for server", default=None)


class Metrics(BaseModel):
    apm_server: APMServer = APMServer()
    export_interval: int = Field(description="How often should we be exporting metrics?", default=5)
    redis: RedisServer = RedisServer()


class Core(BaseModel):
    extensions: set[str] = Field(description="A list of extensions to load", default=set())

    metrics: Metrics = Metrics()
    "Configuration for Metrics Collection"

    redis: RedisServer = RedisServer()
    "Configuration for Redis instances"


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    DISABLED = "DISABLED"


class Logging(BaseModel):
    log_level: LogLevel = Field(  # type: ignore
        description="What level of logging should we have?", default=LogLevel.DEBUG
    )
    log_to_console: bool = Field(description="Should we log to console?", default=True)
    log_to_file: bool = Field(description="Should we log to files on the server?", default=False)
    log_directory: str = Field(
        description="If `log_to_file: true`, what is the directory to store logs?", default="/var/log/clue/"
    )
    log_to_syslog: bool = Field(description="Should logs be sent to a syslog server?", default=False)
    syslog_host: str = Field(
        description="If `log_to_syslog: true`, provide hostname/IP of the syslog server?", default="localhost"
    )
    syslog_port: int = Field(description="If `log_to_syslog: true`, provide port of the syslog server?", default=514)
    export_interval: int = Field(description="How often, in seconds, should counters log their values?", default=5)
    log_as_json: bool = Field(description="Log in JSON format?", default=False)
    heartbeat_file: str | None = Field(
        description=(
            "Add a health check to core components.<br>"
            "If `true`, core components will touch this path regularly to tell the container environment it is healthy"
        ),
        default=None,
    )


class ExternalSource(BaseModel):
    name: str = Field(description="Name of the source.")
    classification: str | None = Field(
        description="Minimum classification applied to information from the source and required to know the "
        "existence of the source.",
        default=CLASSIFICATION.UNRESTRICTED,
    )
    max_classification: str | None = Field(
        description="Maximum classification of data that may be handled by the source", default=None
    )
    url: str = Field(description="URL of the upstream source's lookup service.")
    obo_target: str | None = Field(
        description="The name of a target clue should OBO to before forwarding the token", default=None
    )
    maintainer: str | None = Field(
        description="Email contact in the RFC-5322 format 'Full Name <email_address>'.", default=None
    )
    datahub_link: Url | None = Field(description="Link to datahub entry on this enrichment", default=None)
    documentation_link: Url | None = Field(description="Link to documentation on this enrichment", default=None)
    production: bool = Field(
        description="Is this source ready for production? This will disable model validation for increased speeds",
        default=False,
    )
    include_default: bool = Field(
        description="Should this source be included by default, or only when specifically requested?", default=True
    )
    built_in: bool = Field(default=True, description="Is this a source included in the clue configuration files?")
    default_timeout: float = Field(
        default=30.0, description="How long should clue wait by default for action execution?"
    )

    model_config = ConfigDict(validate_assignment=True)

    @field_validator("maintainer")
    @classmethod
    def validate_maintainer(cls, maintainer: str | None) -> str | None:  # noqa: ANN102
        """Validates the maintainer field.

        Args:
            maintainer (str | None): The maintainer field to validate. If None, it will be passed through.

        Raises:
            AssertionError: Raised whenever the field is in an invalid format.

        Returns:
            str | None: The validated maintainer field.
        """
        if maintainer:
            parsed_addr = parseaddr(maintainer)
            if not (all(parsed_addr) and "@" in parsed_addr[1]):
                raise AssertionError("Maintainer string must be in RFC-5322 format.")

        return maintainer

    @field_validator("classification", "max_classification")
    @classmethod
    def validate_classification(cls, cls_str: str) -> str:  # noqa: ANN102
        """Validates the classification and max_classification fields.

        Args:
            cls_str (str): The classification value to validate.

        Raises:
            AssertionError: Raised whenever the provided classification is not valid.

        Returns:
            str: The validated classification value.
        """
        cls_str = cls_str.upper()

        if not CLASSIFICATION.is_valid(cls_str):
            raise AssertionError(f"{cls_str} is not a valid classification")

        return cls_str


EXAMPLE_EXTERNAL_SOURCE_VT = {
    # This is an example on how this would work with VirusTotal
    "name": "VirusTotal",
    "url": "vt-lookup.namespace.svc.cluster.local",
    "classification": "TLP:CLEAR",
    "max_classification": "TLP:CLEAR",
}

EXAMPLE_EXTERNAL_SOURCE_MB = {
    # This is an example on how this would work with Malware Bazaar
    "name": "Malware Bazaar",
    "url": "mb-lookup.namespace.scv.cluster.local",
    "classification": "TLP:CLEAR",
    "max_classification": "TLP:CLEAR",
}


class OBOService(BaseModel):
    enabled: bool = Field(default=False, description="Is this service available?")
    scope: str = Field(description="The scope to OBO to.")
    quota: int | None = Field(
        default=None, description="Optional quota for the number of concurrent requests per user to this service"
    )


class UI(BaseModel):
    cors_origins: list[str] = Field(default=[], description="List of valid deployments")


class API(BaseModel):
    audit: bool = Field(description="Should API calls be audited and saved to a separate log file?", default=True)
    debug: bool = Field(description="Enable debugging?", default=False)
    discover_url: str | None = Field(description="Discover URL", default=None)
    external_sources: list[ExternalSource] = Field(description="List of external sources to query", default=[])
    obo_targets: dict[str, OBOService] = Field(description="List of targets clue can OBO to", default={})
    secret_key: str = Field(description="Flask secret key to store cookies, etc.", default_factory=lambda: uuid4().hex)
    session_duration: int = Field(
        description="Duration of the user session before the user has to login again", default=3600
    )
    validate_session_ip: bool = Field(
        description="Validate if the session IP matches the IP the session was created from", default=True
    )
    validate_session_useragent: bool = Field(
        description="Validate if the session useragent matches the useragent the session was created with", default=True
    )
    validate_session_xsrf_token: bool = Field(
        description="Validate if the XSRF token matches the randomly generated token for the session", default=True
    )


root_path = Path("/etc") / APP_NAME

config_locations = [
    root_path / "conf" / "config.yml",
    Path(os.environ.get("CLUE_CONF_FOLDER", root_path)) / "config.yml",
]

if os.getenv("AZURE_TEST_CONFIG", None) is not None:
    import re

    logger = logging.getLogger("clue.models.config")
    logger.setLevel(logging.INFO)
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(CLUE_LOG_FORMAT, CLUE_DATE_FORMAT))
    logger.addHandler(console)

    logger.info("Azure build environment detected, adding additional config path")

    work_dir_parent = Path("/__w")
    work_dir: Path | None = None
    for sub_path in work_dir_parent.iterdir():
        if not sub_path.is_dir():
            continue

        logger.info("Testing sub path %s", sub_path)

        if re.match(r"\d+", str(sub_path.name)):
            work_dir = work_dir_parent / sub_path

        if work_dir is not None:
            logger.info("Subpath %s exists, checking for test path", work_dir)
            test_config_path = work_dir / "s" / "test" / "config" / "config.yml"

            if test_config_path.exists():
                config_locations.append(test_config_path)
                logger.info("Path %s added as config path", test_config_path)
                break

            logger.error("Config path not found at path %s", test_config_path)
            logger.info("Available files:\n%s", "\n".join(sorted(str(path) for path in (work_dir / "s").glob("**/*"))))
            work_dir = None


class Config(BaseSettings):
    api: API = API()
    ui: UI = UI()
    auth: Auth = Auth()
    core: Core = Core()
    logging: Logging = Logging()

    model_config = SettingsConfigDict(
        yaml_file=config_locations,
        yaml_file_encoding="utf-8",
        strict=True,
        env_nested_delimiter="__",
    )

    @classmethod
    def settings_customise_sources(
        cls,  # noqa: ANN102
        *args,  # noqa: ANN002
        **kwargs,  # noqa: ANN002, ANN102
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        "Adds a YamlConfigSettingsSource object at the end of the settings_customize_sources response."
        return (*super().settings_customise_sources(*args, **kwargs), YamlConfigSettingsSource(cls))


if __name__ == "__main__":
    # When executed, the config model will print the default values of the configuration
    import json

    import yaml

    print("Schema: ")  # noqa: T201
    print(json.dumps(Config.model_json_schema(), indent=2))  # noqa: T201

    print("\n\nConfig:")  # noqa: T201
    print(yaml.safe_dump(Config().model_dump(mode="json")))  # noqa: T201
