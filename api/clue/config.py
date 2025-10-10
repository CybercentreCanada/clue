import os

from clue.common import forge
from clue.models.config import Config

config: Config = Config()

#################################################################
# Configuration

CLASSIFICATION = forge.get_classification()

AUDIT = config.api.audit

SECRET_KEY = config.api.secret_key
DEBUG = config.api.debug
MAX_CLASSIFICATION = CLASSIFICATION.UNRESTRICTED

USER_TYPES = {"admin", "user"}


def get_version() -> str:
    """The version of the Clue API

    Returns:
        str: The clue version
    """
    return os.environ.get("CLUE_VERSION", "1.0.0.dev0")


def get_commit() -> str:
    """The commit of the currently deployed Clue API

    Returns:
        str: The commit of the currently deployed image
    """
    return os.environ.get("COMMIT_HASH", "this is not the commit you are looking for")


def get_branch() -> str:
    """The branch of the current Clue Image

    Returns:
        str: The current branch
    """
    return os.environ.get("BRANCH", "this is not the branch you are looking for")


def get_redis():
    """The Redis instance used by Clue.

    Returns:
        The Redis client instance.
    """
    from clue.remote.datatypes import get_client

    return get_client(config.core.redis.host, config.core.redis.port, False, password=config.core.redis.password)


cache = forge.cache
