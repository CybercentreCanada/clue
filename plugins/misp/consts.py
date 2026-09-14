import os

# Use clue's timeout const
from clue.plugin.utils import MAX_TIMEOUT as MAX_TIMEOUT


def _str_to_bool(value: str) -> bool:
    """Converts a string to a bool."""
    return value.lower().strip() in ("true", "1")


ACTIONS_ENABLED = _str_to_bool(os.environ.get("ACTIONS_ENABLED", "true"))
CLASSIFICATION = os.environ.get("CLASSIFICATION", "TLP:CLEAR")
MISP_API_KEY = os.environ.get("MISP_API_KEY", "")
MISP_URL = os.environ.get("MISP_URL", "https://misp.local")
SIGHTING_SOURCE = os.environ.get("SIGHTING_SOURCE", "Clue")
EXCLUDE_DECAYED = _str_to_bool(os.environ.get("EXCLUDE_DECAYED", "true"))

_verify_raw = os.environ.get("MISP_VERIFY", "true").strip()
if _verify_raw.lower() in ("true", "1", "false", "0"):
    VERIFY: str | bool = _str_to_bool(_verify_raw)
else:
    VERIFY = _verify_raw  # path to a CA bundle

TYPE_MAPPING: dict[str, list[str]] = {
    "ipv4": ["ip-src", "ip-dst"],
    "ipv6": ["ip-src", "ip-dst"],
    "mac_address": ["mac-address"],
    "domain": ["domain"],
    "url": ["url", "link"],
    "email_address": ["email-src", "email-dst"],
    "sha1": ["sha1"],
    "sha256": ["sha256"],
    "md5": ["md5"],
}

TLP_ENUM = {"TLP:CLEAR": 0, "TLP:GREEN": 1, "TLP:AMBER": 2, "TLP:AMBER+STRICT": 3, "TLP:RED": 4}

# Tags in MISP can be noisy, limit to known high impact tags
# filter tags by "namespace" or "namespace:predicate"
ALLOW_TAGS = {
    "ecsirt",
    "adversary",
    "malware_classification",
    "misp-galaxy:threat-actor",
    "misp-galaxy:malware",
    "misp-galaxy:tool",
    "misp-galaxy:ransomware",
    "misp-galaxy:sector",
}
# Allow users to append or override the default list
if extra := os.environ.get("ALLOW_TAGS_EXTRA"):
    ALLOW_TAGS = ALLOW_TAGS | {t.strip() for t in extra.split(",")}
if override := os.environ.get("ALLOW_TAGS"):
    ALLOW_TAGS = {t.strip() for t in override.split(",")}

# 4 (undefined), defaults to None
THREAT_LEVEL = {
    1: 0.75,  # High
    2: 0.5,  # Medium
    3: 0.25,  # Low
}
