import os
import time
from datetime import datetime

import jwt
from flask import request

from clue.models.network import QueryEntry
from clue.plugin import CluePlugin


def enrich(*args):
    time.sleep(1000)

    return QueryEntry(
        link="https://example.com",
        count=10,
        classification="TLP:WHITE",
        annotations=[
            {
                "type": "opinion",
                "value": "malicious",
                "confidence": 0.7,
                "severity": 1.0,
                "summary": "This is a bad ip",
                "details": "# Breaking news\nThis is a bad IP",
                "analytic": "test enrichment",
                "version": "0.0.1",
                "timestamp": datetime(2024, 1, 1, 1, 1, 1).isoformat(),
            }
        ],
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
    app_name="slow_server",
    supported_types={"ipv4", "ipv6", "port", "sha256"},
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
