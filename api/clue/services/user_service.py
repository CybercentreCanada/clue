from typing import Any

from elasticapm.traces import capture_span
from flask import current_app, request

from clue.common.exceptions import (
    AccessDeniedException,
    ClueValueError,
    InvalidDataException,
)
from clue.common.logging import get_logger
from clue.config import CLASSIFICATION, config, get_redis
from clue.helper.oauth import parse_profile
from clue.models.auth_user import AuthUser
from clue.models.config import ExternalSource
from clue.remote.datatypes.user_quota_tracker import UserQuotaTracker

logger = get_logger(__file__)


@capture_span(span_type="authentication")
def parse_user_data(
    data: dict[str, Any],
    oauth_provider: str,
) -> AuthUser:
    """Convert OAuth user data into a normalized Clue identity.

    Args:
        data: The token data or decoded OAuth profile to parse.
        oauth_provider: The configured provider that issued the data.

    Raises:
        InvalidDataException: If required authentication data is missing.
        AccessDeniedException: If the authenticated identity is not permitted to access Clue.

    Returns:
        The normalized authenticated identity.
    """
    if not data or not oauth_provider:
        raise InvalidDataException("Both the JWT and OAuth provider must be supplied")

    oauth = current_app.extensions.get("authlib.integrations.flask_client")
    if not oauth:
        logger.critical("Authlib integration missing!")
        raise ClueValueError()
    provider = oauth.create_client(oauth_provider)

    if "id_token" in data:
        data = provider.parse_id_token(
            data, nonce=request.args.get("nonce", data.get("userinfo", {}).get("nonce", None))
        )

    oauth_provider_config = config.auth.oauth.providers[oauth_provider]

    if not data:
        raise AccessDeniedException("Not user data contained in the token")

    user_data = parse_profile(data, oauth_provider_config)
    if len(oauth_provider_config.required_groups) > 0:
        required_groups = set(oauth_provider_config.required_groups)
        if len(required_groups) != len(required_groups & set(user_data["groups"])):
            logger.warning(
                f"User {user_data['uname']} is missing groups from their JWT:"
                f" {', '.join(required_groups - (required_groups & set(user_data['groups'])))}"
            )
            raise AccessDeniedException("This user is not allowed access to the system")

    has_access = user_data.pop("access", False)
    if not has_access:
        raise AccessDeniedException("This user is not allowed access to the system")

    get_dynamic_classification(user_data, oauth_provider)

    return AuthUser.model_validate(user_data)


def get_dynamic_classification(user_data: dict[str, Any], oauth_provider: str):
    """Apply configured group-based classification to normalized user data.

    Args:
        user_data: The normalized user data to update.
        oauth_provider: The configured OAuth provider name.
    """
    classification_map = config.auth.oauth.providers[oauth_provider].classification_map
    if len(user_data["groups"]) > 0 and classification_map:
        for group in user_data["groups"]:
            if group in classification_map:
                if not CLASSIFICATION.is_valid(classification_map[group]):
                    logger.warning("Group %s has invalid classification mapping %s", group, classification_map[group])
                    continue

                user_data["classification"] = CLASSIFICATION.max_classification(
                    user_data["classification"], classification_map[group]
                )


QUOTA_TRACKERS: dict[str, UserQuotaTracker] = {}


def check_quota(source: ExternalSource, user: dict[str, Any]) -> str | None:
    "Check that a user does not have too many concurrent requests to a given external service."
    if not source.obo_target:
        return None

    quota = config.api.obo_targets[source.obo_target].quota

    if quota is None:
        return None

    if source.obo_target not in QUOTA_TRACKERS:
        QUOTA_TRACKERS[source.obo_target] = UserQuotaTracker(source.obo_target, timeout=60, redis=get_redis())

    if QUOTA_TRACKERS[source.obo_target].begin(user["uname"], quota):
        logger.debug(
            "User %s is below quota of %s concurrent requests to source %s",
            user["uname"],
            quota,
            source.obo_target,
        )
        return None

    logger.error(
        "User %s has exceeded quota of %s concurrent requests to source %s",
        user["uname"],
        quota,
        source.obo_target,
    )
    return (
        f"You have too many simultaneous connections to external service {source.obo_target}. "
        "Please use larger batches when enriching."
    )


def release_quota(source: ExternalSource, user: dict[str, Any]):
    "Release the space claimed by a given request in the user's quota"
    if not source.obo_target:
        return

    quota = config.api.obo_targets[source.obo_target].quota

    if quota is None:
        return

    if source.obo_target in QUOTA_TRACKERS:
        QUOTA_TRACKERS[source.obo_target].end(user["uname"])
