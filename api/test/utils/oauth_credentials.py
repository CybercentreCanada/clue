import json
import logging

import requests
from requests.exceptions import ConnectionError


def get_token(user=None):
    if not user:
        user = "goose"

    try:
        data = requests.post(
            "http://localhost:9100/realms/HogwartsMini/protocol/openid-connect/token",
            data={
                "username": user,
                "password": user,
                "grant_type": "password",
                "client_id": "clue",
                "client_secret": "09RhSF7tp0ShDdDMCszqI4zk8HMroTTZ",
            },
            timeout=5,
        )
    except ConnectionError:
        logging.exception("Connection Error when authenticating with keycloak")
        return None

    if data.status_code == 200:
        return data.json()["access_token"]
    else:
        logging.error("Non 200 status:", json.dumps(data.json()))

    return None


if __name__ == "__main__":
    print(get_token())  # noqa: T201
