from unittest.mock import patch

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from clue.config import cache
from clue.services import jwt_service
from clue.services.jwt_service import extract_audience
from test.utils.oauth_credentials import get_token


def test_get_jwk_bypasses_stale_cache_for_unknown_key():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = jwt.PyJWK.from_dict(jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key(), as_dict=True))
    token = jwt.encode({"sub": "user"}, private_key, algorithm="RS256", headers={"kid": jwk.key_id or "new-key"})
    key_data = jwk._jwk_data | {"kid": jwt.get_unverified_header(token)["kid"]}

    with (
        patch.object(jwt_service, "get_jwks", return_value=({}, {})),
        patch.object(jwt_service, "_fetch_jwks", return_value=({key_data["kid"]: key_data}, {})) as fetch_jwks,
        patch.object(cache, "delete") as delete_cache,
    ):
        result = jwt_service.get_jwk(token)

    assert result.key_id == key_data["kid"]
    delete_cache.assert_called_once_with(key="get_jwks")
    fetch_jwks.assert_called_once_with()


def test_extract_audience():
    access_token = get_token()

    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    assert "clue" in extract_audience(access_token)
