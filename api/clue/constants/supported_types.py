from typing import NotRequired, TypedDict

from clue.common.logging import get_logger
from clue.common.regex import (
    COMMUNITY_ID_REGEX,
    DOMAIN_ONLY_REGEX,
    EMAIL_PATH_REGEX,
    EMAIL_REGEX,
    IPV4_ONLY_REGEX,
    IPV6_ONLY_REGEX,
    JA3_REGEX,
    JA4_REGEX,
    MAC_ADDRESS_REGEX,
    MD5_REGEX,
    PORT_REGEX,
    SHA1_REGEX,
    SHA256_REGEX,
    URI_ONLY,
    UUID4_REGEX,
    ZEEK_ID_REGEX,
)

logger = get_logger(__file__)


class SupportedType(TypedDict):
    """Type detection metadata; an omitted priority is equivalent to zero."""

    regex: str | None
    case_sensitive: bool
    priority: NotRequired[int]


SUPPORTED_TYPES: dict[str, SupportedType] = {
    "ipv4": {"regex": IPV4_ONLY_REGEX, "case_sensitive": True, "priority": 10},
    "ipv6": {"regex": IPV6_ONLY_REGEX, "case_sensitive": True, "priority": 10},
    # We don't auto-detect ip types, as it's redundant with ipv4/v6. This is just a convenience/backwards compat thing
    "ip": {"regex": None, "case_sensitive": False},
    "asn": {"regex": None, "case_sensitive": True},
    "domain": {"regex": DOMAIN_ONLY_REGEX, "case_sensitive": False},
    "port": {"regex": PORT_REGEX, "case_sensitive": False},
    "url": {"regex": URI_ONLY, "case_sensitive": True},
    "userid": {"regex": None, "case_sensitive": True},
    "user_agent": {"regex": None, "case_sensitive": True},
    "email_address": {"regex": EMAIL_REGEX, "case_sensitive": True},
    "email_id": {"regex": None, "case_sensitive": True},
    "email_path": {"regex": EMAIL_PATH_REGEX, "case_sensitive": True},
    "md5": {"regex": MD5_REGEX, "case_sensitive": True},
    "sha1": {"regex": SHA1_REGEX, "case_sensitive": True},
    "sha256": {"regex": SHA256_REGEX, "case_sensitive": True},
    "telemetry": {"regex": None, "case_sensitive": True},
    "hostname": {"regex": None, "case_sensitive": True},
    "tenant_id": {"regex": UUID4_REGEX, "case_sensitive": False},
    "mac_address": {"regex": MAC_ADDRESS_REGEX, "case_sensitive": False},
    "command_line": {"regex": None, "case_sensitive": True},
    "community_id": {"regex": COMMUNITY_ID_REGEX, "case_sensitive": True},
    "ja3": {"regex": JA3_REGEX, "case_sensitive": True},
    "ja4": {"regex": JA4_REGEX, "case_sensitive": True},
    "zeek_id": {"regex": ZEEK_ID_REGEX, "case_sensitive": True},
}


# Retained for selector normalization and extensions importing the legacy list.
CASE_INSENSITIVE_TYPES = [
    type_name for type_name, metadata in SUPPORTED_TYPES.items() if not metadata["case_sensitive"]
]


def add_supported_type(
    type: str,
    regex: str | None = None,
    namespace: str | None = None,
    case_insensitive: bool = False,
    priority: int = 0,
) -> None:
    r"""Add a supported type to the SUPPORTED_TYPES registry.

    This function registers a new type with an optional regex pattern for validation.
    The type can be added to either the default namespace or a custom namespace.

    Args:
        type (str): The name of the type to be added.
        regex (str | None, optional): A regex pattern for validating the type. Defaults to None.
        namespace (str | None, optional): The namespace for the type. If None, adds to default namespace.
            Defaults to None.
        case_insensitive (bool, optional): Whether matching and selector normalization ignore case. Defaults to False.
        priority (int, optional): Detection priority; higher values win, with registry insertion order breaking ties.
            Defaults to 0. Negative values are allowed.

    Returns:
        None

    Examples:
        >>> add_supported_type("email", r"^[\w\.-]+@[\w\.-]+\.\w+$")
        >>> add_supported_type("custom_id", r"^\d{5}$", namespace="myapp")
    """
    if not namespace:
        logger.info("Adding new type %s to the default namespace with regex %s", type, regex)
        new_entry = type
    else:
        logger.info("Adding type %s to namespace %s with regex %s", type, namespace, regex)
        new_entry = f"{namespace}_{type}"

    SUPPORTED_TYPES[new_entry] = {"regex": regex, "case_sensitive": not case_insensitive, "priority": priority}
    if case_insensitive and new_entry not in CASE_INSENSITIVE_TYPES:
        CASE_INSENSITIVE_TYPES.append(new_entry)
    elif not case_insensitive and new_entry in CASE_INSENSITIVE_TYPES:
        CASE_INSENSITIVE_TYPES.remove(new_entry)
