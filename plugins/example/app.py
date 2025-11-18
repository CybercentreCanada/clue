"""This is an example module.

Status: In Development
"""

import os
import textwrap

from clue.common.logging import get_logger
from clue.models.network import Annotation, QueryEntry
from clue.plugin import CluePlugin
from clue.plugin.utils import Params
from pydantic_core import Url

CLASSIFICATION = os.environ.get("CLASSIFICATION", "TLP:CLEAR")

logger = get_logger(__file__)

plugin = CluePlugin(
    app_name=os.environ.get("APP_NAME", "test-plugin"),
    classification=CLASSIFICATION,
    supported_types="ipv4,ipv6,domain,url,email_address",
    logger=logger,
)


@plugin.use
def enrich(type_name: str, value: str, params: Params, *_args) -> QueryEntry:
    "Enrich a given indicator"
    logger.info(f"Enriching [{type_name}] {value} limit {params.limit} (annotate={params.annotate})")

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
