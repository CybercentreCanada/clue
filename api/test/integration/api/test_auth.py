import re
from urllib.parse import urlsplit

import pytest
import requests

from clue.security.utils import decode_jwt_payload
from clue.services import jwt_service
from test.utils.oauth_credentials import get_token


def test_oauth_flow(host):
    session = requests.Session()

    res = session.get(f"{host}/api/v1/auth/login/?provider=keycloak")

    for past in res.history:
        assert past.ok and past.status_code >= 300

    assert res.ok
    assert res.url.startswith("http://localhost:9100/realms/HogwartsMini/protocol/openid-connect/auth")

    url = re.sub(r'[\s\S]+<form.+action="(.+?)".+>[\s\S]+', r"\1", res.text).replace("&amp;", "&")

    thing = session.post(url, data={"username": "goose", "password": "goose"}, allow_redirects=False)

    final_data = session.get(
        f"{host}/api/v1/auth/login/?{urlsplit(thing.headers['Location']).query}",
        cookies={
            # No clue why this is necessary tbh
            "session": session.cookies["session"]
        },
    ).json()

    assert final_data["api_status_code"] == 200
    app_token = final_data["api_response"]["app_token"]

    result = requests.get(
        f"{host}/api/v1/",
        headers={"Authorization": f"Bearer {app_token}"},
    )

    assert result.ok


def test_bearer_token_direct(host):
    access_token = get_token()

    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    res = requests.get(
        f"{host}/api/v1/",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert res.ok


def test_sa_jwt():
    result = jwt_service.fetch_sa_token()
    assert result and "." in result

    jwt = decode_jwt_payload(result)

    assert "goose@clue.cyber.gc.ca" in jwt["email"]
