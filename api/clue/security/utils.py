import base64
import json
import os
from typing import Any

UPPERCASE = r"[A-Z]"
LOWERCASE = r"[a-z]"
NUMBER = r"[0-9]"
SPECIAL = r'[ !#$@%&\'()*+,-./[\\\]^_`{|}~"]'
PASS_BASIC = (
    [chr(x + 65) for x in range(26)]
    + [chr(x + 97) for x in range(26)]
    + [str(x) for x in range(10)]
    + ["!", "@", "$", "^", "?", "&", "*", "(", ")"]
)


def generate_random_secret(length: int = 25) -> str:
    """Generate a random secret

    Args:
        length (int, optional): The length of the secret. Defaults to 25.

    Returns:
        str: The random secret
    """
    return base64.b32encode(os.urandom(length)).decode("UTF-8")


def decode_jwt_payload(jwt: str) -> dict[str, Any]:
    "Decode a JWT payload. DOES NOT VALIDATE THE JWT, DO NOT USE THIS TO VALIDATE THE TOKEN."
    payload = jwt.split(".")[1]

    return json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)).decode())
