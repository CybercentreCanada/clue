import hashlib
import re
from typing import Any, Optional

import elasticapm

from clue.common.logging import get_logger
from clue.config import CLASSIFICATION as CL_ENGINE
from clue.config import USER_TYPES, config
from clue.models.config import (
    DEFAULT_EMAIL_FIELDS,
    DEFAULT_USER_FIELDS,
    DEFAULT_USER_NAME_FIELDS,
    OAuthProvider,
)

VALID_CHARS = [str(x) for x in range(10)] + [chr(x + 65) for x in range(26)] + [chr(x + 97) for x in range(26)] + ["-"]

logger = get_logger(__file__)


def reorder_name(name: Optional[str]) -> Optional[str]:
    """Reorders a name, so that the last name goes in front of the first name.

    Args:
        name (Optional[str]): The name to reorder

    Returns:
        Optional[str]: The reordered name
    """
    if name is None:
        return name

    return " ".join(name.split(", ", 1)[::-1])


@elasticapm.capture_span(span_type="authentication")
def parse_profile(profile: dict[str, Any], provider_config: OAuthProvider) -> dict[str, Any]:  # noqa: C901
    """Find email address and normalize it for further processing"""
    email_adr: str | None = None
    for field in DEFAULT_EMAIL_FIELDS:
        if field in profile:
            email_adr = profile[field]
            if isinstance(email_adr, list):
                email_adr = email_adr[0]
            break

    if isinstance(email_adr, list):
        email_adr = email_adr[0]

    if email_adr:
        email_adr = email_adr.lower()
        if "@" not in email_adr:
            email_adr = None

    # Find the name of the user
    name = None
    for field in DEFAULT_USER_NAME_FIELDS:
        if field in profile:
            name = reorder_name(profile[field])
            break

    # Try to find a username or use email address
    uname = None
    for field in DEFAULT_USER_FIELDS:
        if field in profile:
            uname: str = profile[field]
            break
    uname = uname or email_adr

    # Did we use the email address?
    if uname is not None and email_adr is not None and uname.lower() == email_adr.lower():
        # 1. Use provided regex matcher
        if provider_config.uid_regex:
            match = re.match(provider_config.uid_regex, uname)
            if match:
                if provider_config.uid_format:
                    uname = provider_config.uid_format.format(*[x or "" for x in match.groups()]).lower()
                else:
                    uname = "".join([x for x in match.groups() if x]).lower()

        # 2. Parse name and domain from email if regex failed or missing
        if uname is not None and uname == email_adr:
            e_name, e_dom = uname.split("@", 1)
            uname = f"{e_name}-{e_dom.split('.')[0]}"

    # 3. Use name as username if there are no username found yet
    if uname is None and name is not None:
        uname = name.replace(" ", "-")

    # Cleanup username
    if uname:
        uname = "".join([c for c in uname if c in VALID_CHARS])

    # Get avatar from gravatar
    if config.auth.oauth.gravatar_enabled and email_adr:
        email_hash = hashlib.md5(email_adr.encode("utf-8")).hexdigest()  # noqa: S324
        alternate = f"https://www.gravatar.com/avatar/{email_hash}?s=256&d=404&r=pg"
    else:
        alternate = None

    # Compute access, roles and classification using auto_properties
    access = True
    roles = ["user"]
    # TODO: correctly figure out the classification
    classification = CL_ENGINE.UNRESTRICTED

    # Infer roles from groups
    if profile.get("groups") and provider_config.role_map:
        for user_type in USER_TYPES:
            if (
                user_type in provider_config.role_map
                and provider_config.role_map[user_type] in profile.get("groups", [])
                and user_type not in roles
            ):
                roles.append(user_type)

    return dict(
        access=access,
        type=roles,
        classification=classification,
        uname=uname,
        name=name,
        email=email_adr,
        password="__NO_PASSWORD__",  # noqa: S106
        avatar=profile.get("picture", alternate),
        groups=profile.get("groups", []),
    )
