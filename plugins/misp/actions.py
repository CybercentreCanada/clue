from typing import Literal

from client import misp_request
from clue.common.exceptions import NotFoundException
from clue.models.actions import ExecuteRequest
from consts import MAX_TIMEOUT, SIGHTING_SOURCE
from pydantic import Field

# MISP has a third type, 'expiration' intentionally left out.
# Sightings are submitted by value, so it would expire every matching attribute.
# Expiry is a per attribute lifecycle decision, not selector level.
SightingType = Literal["true positive", "false positive"]
SIGHTING_TYPE_IDS: dict[SightingType, str] = {"true positive": "0", "false positive": "1"}


class ReportSighting(ExecuteRequest):
    """Parameters for the report_sighting action

    Sightings are submitted by value, MISP records one against every attribute
    matching it, a single reporting can span multiple events.

    Attributes:
        sighting_type: What type of sighting is being reported
    """

    sighting_type: SightingType = Field(default="true positive", description="Type of sighting to report")


def report_sighting(values: list[str], request: ReportSighting):
    """Reports a list of sightings using provided values to MISP.

    Raises:
        NotFoundException: If MISP reports no changes
    """
    payload = {"values": values, "type": SIGHTING_TYPE_IDS[request.sighting_type], "source": SIGHTING_SOURCE}

    # MISP's response returns a single sighting, not every attribute it matched, so there's
    # nothing useful to take from it; other than if ANY change was made.
    data = misp_request("post", "/sightings/add", MAX_TIMEOUT, json=payload)

    if not isinstance(data, dict) or "Sighting" not in data:
        raise NotFoundException
