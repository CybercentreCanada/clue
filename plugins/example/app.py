"""This module was created by CCCS.

Team: CCCS

Point of Contact: [Matthew Rafuse] <matthew.rafuse@cyber.gc.ca>

Status: Development


"""

import os
import textwrap

from clue.common.exceptions import InvalidDataException
from clue.common.logging import get_logger
from clue.models.network import Annotation, QueryEntry
from clue.plugin import CluePlugin
from clue.plugin.utils import Params
from pydantic_core import Url

CLASSIFICATION = os.environ.get("CLASSIFICATION", "TLP:CLEAR")
TYPES = {"ipv4", "ipv6", "domain", "url", "email_address"}

logger = get_logger(__file__)


def enrich(type_name: str, value: str, params: Params, *_args) -> QueryEntry:
    "Enrich a given indicator"
    if type_name not in TYPES:
        raise InvalidDataException(
            message=f"Type name `{type_name}` is invalid. Valid types are: {', '.join(TYPES)}"
        )

    logger.info(
        f"Enriching [{type_name}] {value} limit {params.limit} (annotate={params.annotate})"
    )

    return QueryEntry(
        classification=CLASSIFICATION,
        count=1,
        link=Url("https://example.com"),
        annotations=[
            Annotation(
                analytic="Test Plugin",
                analytic_icon="fluent-color:checkmark-circle-16",
                icon="fluent-color:checkmark-circle-16",
                type="context",
                value=value,
                link=Url("https://example.com"),
                details=textwrap.dedent(
                    f"""
                # Test Enrichment

                Type: {type_name}

                Value: {value}
                """
                ),
                summary=f"Test Enrichment - type: {type_name}, value: {value}",
                confidence=1.0,
            )
        ],


    )


plugin = CluePlugin(
    app_name=os.environ.get("APP_NAME", "test-plugin"),
    classification=CLASSIFICATION,
    enable_apm=False,
    enable_cache=True,
    enrich=enrich,
    supported_types=TYPES,
    logger=logger,
)


app = plugin.app


def main():
    """Main application function"""
    plugin.app.run(
        host="0.0.0.0",  # noqa: S104
        port=int(os.environ.get("PLUGIN_PORT", os.environ.get("PORT", 8000))),
        debug=bool(os.environ.get("DEBUG", "False").capitalize()),
    )


if __name__ == "__main__":
    main()
