from clue.common.str_utils import default_string_value
from clue.config import CLASSIFICATION, config, get_branch, get_commit, get_version
from clue.helper.discover import get_apps_list

classification_definition = CLASSIFICATION.get_parsed_classification_definition()

apps = get_apps_list()


def get_configuration():
    """Get system configration data for the Clue API

    Args:
        user (User): The user making the request
    """
    return {
        "configuration": {
            "auth": {
                "oauth_providers": [
                    name
                    for name, p in config.auth.oauth.providers.items()
                    if default_string_value(p.client_secret, env_name=f"{name.upper()}_CLIENT_SECRET")
                ],
                # "internal": {"enabled": config.auth.internal.enabled},
            },
            "system": {
                # "type": config.system.type,
                "version": get_version(),
                "branch": get_branch(),
                "commit": get_commit(),
            },
            "ui": {
                "apps": apps,
                "cors_origins": config.ui.cors_origins,
            },
        },
        "c12nDef": classification_definition,
    }
