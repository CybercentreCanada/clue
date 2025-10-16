import json
from datetime import datetime
from pathlib import Path
from typing import cast

from clue.common.logging import get_logger
from clue.models.network import Annotation
from pydantic_core import Url

logger = get_logger(__file__)

with (Path(__file__).parent / "data.json").open("r") as _wiki_data:
    WIKIPEDIA_DATA: list[dict[str, int | str]] = json.load(_wiki_data)


def fetch_port_information(port: int) -> list[Annotation]:
    "Get unofficial information on ports from wikipedia; Used as a fallback if IANA database does not exist"
    logger.info("IANA official designation missing for port %s, falling back to wikipedia", port)

    matching_rows = [row for row in WIKIPEDIA_DATA if cast(int, row["start"]) <= port and cast(int, row["end"]) >= port]

    port_data = [
        Annotation(
            analytic="IANA Port Allocation",
            type="context",
            value=row["value"],
            summary="Information sourced from wikipedia",
            link=Url("https://en.wikipedia.org/wiki/List_of_TCP_and_UDP_port_numbers"),
            details=cast(str, row["summary"]),
            timestamp=datetime.fromisoformat(cast(str, row["timestamp"])),
            confidence=1.0,
        )
        for row in matching_rows
    ]

    return port_data
