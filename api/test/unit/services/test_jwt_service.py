from unittest.mock import patch

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from clue.config import cache
from clue.services import jwt_service
from clue.services.jwt_service import extract_audience
from test.utils.oauth_credentials import get_token


def test_get_jwk_refreshes_the_cache_for_an_unknown_key():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    key_data = jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key(), as_dict=True) | {"kid": "new-key"}
    token = jwt.encode({"sub": "user"}, private_key, algorithm="RS256", headers={"kid": key_data["kid"]})

    with (
        patch.object(jwt_service, "get_jwks", side_effect=[({}, {}), ({key_data["kid"]: key_data}, {})]) as get_jwks,
        patch.object(cache, "delete") as delete_cache,
    ):
        result = jwt_service.get_jwk(token)

    assert result.key_id == key_data["kid"]
    delete_cache.assert_called_once_with(key="get_jwks")
    assert get_jwks.call_count == 2


def test_extract_audience():
    access_token = get_token()

    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    assert "clue" in extract_audience(access_token)
