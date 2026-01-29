from clue.common.logging import get_logger
from clue.common.regex import (
    DOMAIN_ONLY_REGEX,
    EMAIL_PATH_REGEX,
    EMAIL_REGEX,
    IPV4_ONLY_REGEX,
    IPV6_ONLY_REGEX,
    MD5_REGEX,
    PORT_REGEX,
    SHA1_REGEX,
    SHA256_REGEX,
    URI_ONLY,
    UUID4_REGEX,
)

logger = get_logger(__file__)

SUPPORTED_TYPES = {
    "ipv4": IPV4_ONLY_REGEX,
    "ipv6": IPV6_ONLY_REGEX,
    # We don't auto-detect ip types, as it's redundant with ipv4/v6. This is just a convenience/backwards compat thing
    "ip": None,
    "domain": DOMAIN_ONLY_REGEX,
    "port": PORT_REGEX,
    "url": URI_ONLY,
    "userid": None,
    "user_agent": None,
    "email_address": EMAIL_REGEX,
    "email_id": None,
    "email_path": EMAIL_PATH_REGEX,
    "md5": MD5_REGEX,
    "sha1": SHA1_REGEX,
    "sha256": SHA256_REGEX,
    "telemetry": None,
    "hostname": None,
    "tenant-id": UUID4_REGEX,
}

CASE_INSENSITIVE_TYPES = ["ip", "domain", "port", "tenant-id", "hbs_oid", "hbs_agent_id"]


def add_supported_type(
    type: str, regex: str | None = None, namespace: str | None = None, case_insensitive: bool = False
):
    r"""Add a supported type to the SUPPORTED_TYPES registry.

    This function registers a new type with an optional regex pattern for validation.
    The type can be added to either the default namespace or a custom namespace.

    Args:
        type (str): The name of the type to be added.
        regex (str | None, optional): A regex pattern for validating the type. Defaults to None.
        namespace (str | None, optional): The namespace for the type. If None, adds to default namespace.
            Defaults to None.

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

    SUPPORTED_TYPES[new_entry] = regex
    if case_insensitive:
        CASE_INSENSITIVE_TYPES.append(new_entry)
