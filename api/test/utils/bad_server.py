"""Example interface for federated lookup plugins/extensions.

Defines the require API required to be implemented in order for federated
lookups to be performed against external systems in Clue.

These implemented microservices are responsible for translating the Clue types into the
correct lookups for the external services.

To allow for extended use by non-AL systems, these type mappings should also be configurable.
"""

import os

import jwt
from flask import request

from clue.models.network import QueryEntry
from clue.plugin import CluePlugin


def enrich(*args):
    return QueryEntry.model_construct(
        classification="TLP:WHITE",
        count="abc123",
        link="https://example.com",
        annotations=[{"abc": "def", "analytic": "banana", "version": "0.0.1"}],
        raw_data=[{"classification": "TLP:CLEAR", "data": '{"test": "raw data"}'}],
    )


def validate_token():
    header = request.headers.get("Authorization", None)
    if not header:
        return None, "Missing auth header"

    token = header.split(" ")[1]

    if "." not in token:
        return None, "Not a JWT"

    user = jwt.decode(jwt=token, options={"verify_aud": False, "verify_signature": False})

    if not user:
        return None, "No user parsed"

    return token, None


plugin = CluePlugin(
    app_name="server",
    supported_types={"port", "sha256", "ipv4", "ipv6"},
    enrich=enrich,
    classification="TLP:WHITE",
    enable_apm=False,
    enable_cache=False,
    validate_token=validate_token,
)

app = plugin.app


def main():
    PORT = os.environ.get("PLUGIN_PORT", 10768)  # noqa: N806
    plugin.app.run(host="0.0.0.0", port=PORT, debug=False)


if __name__ == "__main__":
    main()
