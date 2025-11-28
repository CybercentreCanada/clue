from typing import Any

import requests

from clue.common.logging import get_logger
from clue.config import config
from clue.constants.env import TESTING

logger = get_logger(__file__)


def get_apps_list() -> list[dict[str, str]]:
    """Get a list of apps from the discovery service

    Returns:
        list[dict[str, str]]: A list of other apps
    """
    apps: list[dict[str, Any]] = []

    if TESTING:
        return apps

    if config.api.discover_url:
        try:
            resp = requests.get(config.api.discover_url, headers={"accept": "application/json"}, timeout=5)

            if not resp.ok:
                logger.warning(
                    "Invalid response %s from server for apps discovery: %s", resp.status_code, config.api.discover_url
                )
                return apps

            data = resp.json()
            for app in data["applications"]["application"]:
                url = app["instance"][0]["hostName"]

                if "clue" not in url:
                    apps.append(
                        {
                            "alt": app["instance"][0]["metadata"]["alternateText"],
                            "name": app["name"],
                            "img_d": app["instance"][0]["metadata"]["imageDark"],
                            "img_l": app["instance"][0]["metadata"]["imageLight"],
                            "route": url,
                            "classification": app["instance"][0]["metadata"]["classification"],
                        }
                    )
        except Exception:
            logger.exception(f"Failed to get apps from discover URL: {config.api.discover_url}")

    return sorted(apps, key=lambda k: k["name"])
