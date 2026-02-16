import base64


def to_base64(_bytes: bytes, encoding: str = "utf-8") -> str:
    """Encode bytes to a base64 string.

    Args:
        _bytes (bytes): The bytes to encode.
        encoding (str, optional): The encoding to use for the decoded string. Defaults to "utf-8".

    Returns:
        str: The base64 encoded string.
    """
    return base64.b64encode(_bytes).decode(encoding)
