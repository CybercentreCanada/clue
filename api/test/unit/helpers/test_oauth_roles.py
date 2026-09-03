import pytest
from pydantic import ValidationError

from clue.helper.oauth import parse_profile
from clue.models.auth_user import AuthUser, UserRole
from clue.models.config import OAuthProvider


def test_parse_profile_maps_configured_group_to_admin_role():
    provider = OAuthProvider.model_construct(
        role_map={UserRole.ADMIN: "clue_admin"},
        uid_regex=None,
        uid_format=None,
    )

    profile = parse_profile(
        {
            "preferred_username": "analyst",
            "email": "analyst@example.com",
            "groups": ["clue_admin"],
        },
        provider,
    )

    assert set(profile["roles"]) == {UserRole.USER, UserRole.ADMIN}


def test_AuthUser_rejects_unknown_role():
    with pytest.raises(ValidationError):
        AuthUser(
            uname="analyst",
            email="analyst@example.com",
            classification="TLP:CLEAR",
            roles={"owner"},  # type: ignore[arg-type]
        )
