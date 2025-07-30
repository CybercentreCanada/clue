import os

import pytest
from pydantic import ValidationError

from clue.models.config import (
    Auth,
    OAuth,
    OAuthProvider,
    ServiceAccount,
    ServiceAccountCreds,
)


def test_service_account():
    with pytest.raises(ValidationError) as err:
        ServiceAccount(enabled=True, accounts=[ServiceAccountCreds(username="potato", provider="keycloak")])

    assert "password" in str(err)

    os.environ["SA_KEYCLOAK_PASSWORD"] = "potato"

    ServiceAccount(enabled=True, accounts=[ServiceAccountCreds(username="potato", provider="keycloak")])

    with pytest.raises(ValidationError) as err:
        ServiceAccount(
            enabled=True,
            accounts=[
                ServiceAccountCreds(username="potato", provider="keycloak"),
                ServiceAccountCreds(username="potato", provider="keycloak"),
            ],
        )

    assert "You may only have one service account per provider" in str(err)

    os.environ.pop("SA_KEYCLOAK_PASSWORD")


def test_auth_validation():
    with pytest.raises(ValidationError) as err:
        Auth(oauth=OAuth(enabled=False), service_account=ServiceAccount(enabled=True))

    assert "In order to use service accounts to connect to plugins" in str(err)

    with pytest.raises(ValidationError) as err:
        Auth(
            oauth=OAuth(enabled=True),
            service_account=ServiceAccount(
                enabled=True, accounts=[ServiceAccountCreds(username="potato", provider="potato", password="potato")]
            ),
        )

    assert "potato is used to connect to non-existent provider potato." in str(err)

    Auth(
        oauth=OAuth(
            enabled=True,
            providers={
                "potato": OAuthProvider(
                    client_id="potato",
                    access_token_url="potato",
                    authorize_url="potato",
                    api_base_url="potato",
                    audience="potato",
                    scope="potato",
                    jwks_uri="potato",
                )
            },
        ),
        service_account=ServiceAccount(
            enabled=True, accounts=[ServiceAccountCreds(username="potato", provider="potato", password="potato")]
        ),
    )
