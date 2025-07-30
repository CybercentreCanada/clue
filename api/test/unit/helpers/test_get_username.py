import base64
import json

from clue.plugin.helpers.token import get_username


def test_get_username():
    jwt_data = {
        "name": "Sir Example User PennyWise & thy third",
        "email": "email",
        "upn": "upn",
        "preferred_username": "preferred_username",
        "unique_name": "unique_name",
    }

    token = "token." + base64.b64encode(json.dumps(jwt_data).encode()).decode()

    assert get_username(token) == "email"

    assert get_username(token, claims=[]) == "sir_example_user_pennywise_thy_third"

    assert get_username(token, claims=["potato", "preferred_username"]) == "preferred_username"
