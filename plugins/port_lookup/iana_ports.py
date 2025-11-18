import csv
import datetime
from pathlib import Path
from typing import Annotated, Literal, Optional, Tuple

from clue.models.network import Annotation
from pydantic import BaseModel, BeforeValidator, ConfigDict

# https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml
# This parses rows from the IANA provided CSV into a Pydantic model (with validators to remove ambiguity
# from the CSV data) & converts these to a dictionary for lookups for a set of Clue annotations


def _parse_port_range(port_no: str) -> Tuple[int, int]:
    """Unpack a port number if it is actually a range"""
    port_start = None
    port_end = None

    if "-" in port_no:
        start, end = port_no.split("-")
        port_start = int(start)
        port_end = int(end)
    else:
        port_start = port_end = int(port_no)

    return (port_start, port_end)


# Convert empty strings to None
StrOrNone = Annotated[Optional[str], BeforeValidator(lambda v: None if v == "" else v)]


class PortAllocation(BaseModel):
    """IANA Port Allocation record, parsed from CSV rows."""

    # The IANA CSV uses Capital Case for field values
    model_config = ConfigDict(
        alias_generator=lambda field_name: " ".join(w.capitalize() for w in field_name.split("_"))
    )

    service_name: str
    port_number: Annotated[Tuple[int, int], BeforeValidator(_parse_port_range)]
    transport_protocol: Literal["tcp"] | Literal["udp"] | Literal["sctp"] | Literal["dccp"]
    description: StrOrNone
    registration_date: StrOrNone
    modification_date: StrOrNone
    reference: StrOrNone
    service_code: StrOrNone
    unauthorized_use_reported: StrOrNone
    assignment_notes: StrOrNone


def _read_port_row(row: dict[str, str]) -> Optional[PortAllocation]:
    """Convert a CSV row to a port allocation"""
    # Check for mandatory fields; there are additional explanatory rows that aren't useful here
    # Saves us from having to specifically check Pydantic errors
    for req_field in ["Port Number", "Service Name", "Transport Protocol"]:
        if row[req_field] == "":
            return None

    return PortAllocation.model_validate(row)


def _read_port_allocations() -> dict[int, list[PortAllocation]]:
    """Reads the on-disk port allocations into a lookup dictionary."""
    port_mappings: dict[int, list[PortAllocation]] = {}

    with open(Path(__file__).parent / "service-names-port-numbers.csv", "r", newline="") as file:
        csv_reader = csv.DictReader(file)

        for row in csv_reader:
            allocation = _read_port_row(row)

            if allocation is None:
                continue

            for port in range(allocation.port_number[0], allocation.port_number[1] + 1):
                if port not in port_mappings:
                    port_mappings[port] = []

                found_dup = False

                # Deduplicate based on service name & description
                # This could be a different structure but these lists are small
                for existing_entry in port_mappings[port]:
                    if (
                        allocation.description == existing_entry.description
                        or allocation.service_name == existing_entry.service_name
                    ):
                        found_dup = True
                        break

                if found_dup:
                    continue

                port_mappings[port].append(allocation)

    return port_mappings


def _allocation_to_annotation(row: PortAllocation) -> Annotation:
    """Converts the internal PortAllocation structure to a Clue annotation"""
    # Not all rows are available in the CSV, so dynamically build a description that includes only
    # rows that exist
    desc_rows = [
        f"{label}: {value}"
        for (label, value) in [
            ("Service Name", row.service_name),
            ("Description", row.description),
            ("Registration Date", row.registration_date),
            ("Reference", row.reference),
            ("Transport Protocol", row.transport_protocol),
        ]
        if value is not None
    ]
    desc = "\n".join(desc_rows)

    modification_date = None
    if row.modification_date is not None:
        modification_date = datetime.datetime.fromisoformat(row.modification_date)

    return Annotation(
        analytic="IANA Port Allocation",
        type="context",
        value=row.service_name,
        details=desc,
        timestamp=modification_date,
        summary=row.description or row.service_name,
        confidence=1.0,
    )


def read_port_annotations() -> dict[int, list[Annotation]]:
    """Builds the in-memory port lookup structure for Clue in Annotation form."""
    lookup = _read_port_allocations()

    annotations = {}

    for port, allocations in lookup.items():
        annotations[port] = [_allocation_to_annotation(allocation) for allocation in allocations]

    return annotations
