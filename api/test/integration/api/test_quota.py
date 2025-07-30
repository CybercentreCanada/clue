import pytest
import requests

from clue.config import get_redis
from clue.remote.datatypes.user_quota_tracker import UserQuotaTracker
from test.utils.oauth_credentials import get_token


# noinspection PyUnusedLocal
def test_quota(host):
    access_token = get_token()  # noqa: F821

    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    quota = UserQuotaTracker("test-obo", 120, redis=get_redis())

    quota.end("goose")
    quota.end("goose")
    quota.end("goose")
    quota.end("goose")
    quota.end("goose")
    assert quota.begin("goose", 3)
    assert quota.begin("goose", 3)
    assert quota.begin("goose", 3)
    assert not quota.begin("goose", 3)

    res = requests.get(
        f"{host}/api/v1/lookup/enrich/ipv4/127.0.0.1",
        params={"max_timeout": 2.0, "sources": "quota-test"},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert res.ok

    assert res.json()["api_response"]["quota-test"]["error"] == (
        "You have too many simultaneous connections to external service test-obo. "
        "Please use larger batches when enriching."
    )

    quota.end("goose")
    quota.end("goose")
    quota.end("goose")
    quota.end("goose")
