
import pytest

from clue.services.auth_service import extract_audience
from test.utils.oauth_credentials import get_token


def test_extract_audience():
    access_token = get_token()

    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    assert "clue" in extract_audience(access_token)
