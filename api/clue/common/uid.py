import hashlib
import uuid
from typing import Any, Literal, Optional

TINY = 8
SHORT = 16
MEDIUM = NORMAL = 32
LONG = 64


def get_random_id() -> str:
    """Generates a random unique id, using uuid4 and encoded in base62

    Returns:
        str: Base62 encoded uuid4
    """
    import baseconv

    return baseconv.base62.encode(uuid.uuid4().int)


def get_id_from_data(data: Any, prefix: Optional[str] = None, length: Literal[8, 16, 32, 64] = MEDIUM):  # type: ignore[assignment]
    """Generates an id based on the provided data, using sha256, truncated to the specified length and encoded in base62

    Args:
        data (Any): The data to use to generate the id
        prefix (Optional[str], optional): Defaults to None.
        length (Literal[8, 16, 32, 64], optional): Defaults to 32.

    Raises:
        ValueError: Raised when an invalid length is provided

    Returns:
        str: The generated base62 encoded truncated sha256 hash.
    """
    import baseconv

    possible_len = [TINY, SHORT, MEDIUM, LONG]
    if length not in possible_len:
        raise ValueError(f"Invalid hash length of {length}. Possible values are: {str(possible_len)}.")
    sha256_hash = hashlib.sha256(str(data).encode()).hexdigest()[:length]
    _hash = baseconv.base62.encode(int(sha256_hash, 16))

    if isinstance(prefix, str):
        _hash = f"{prefix}_{_hash}"

    return _hash
