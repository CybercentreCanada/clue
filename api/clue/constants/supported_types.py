from clue.common.regex import (
    DOMAIN_ONLY_REGEX,
    EMAIL_PATH_REGEX,
    EMAIL_REGEX,
    HBS_AGENT_ID_REGEX,
    IPV4_ONLY_REGEX,
    IPV6_ONLY_REGEX,
    MD5_REGEX,
    PORT_REGEX,
    SHA1_REGEX,
    SHA256_REGEX,
    URI_ONLY,
    UUID4_REGEX,
)

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
    "hbs_oid": None,
    "hbs_agent_id": HBS_AGENT_ID_REGEX,
    "telemetry": None,
    "howler_id": None,
    "hostname": None,
    "tenant-id": UUID4_REGEX,
}

CASE_INSENSITIVE_TYPES = ["ip", "domain", "port", "tenant-id", "hbs_oid", "hbs_agent_id"]
