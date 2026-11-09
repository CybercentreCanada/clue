"""Enrich autonomous system numbers with names published by the RIPE NCC."""

import os
import re
from pathlib import Path
from typing import NamedTuple

from clue.common.exceptions import InvalidDataException
from clue.common.logging import get_logger
from clue.models.network import Annotation, QueryEntry
from clue.plugin import CluePlugin
from clue.plugin.utils import Params

APP_NAME = os.environ.get("APP_NAME", "ripe-asn-names")
CLASSIFICATION = os.environ.get("CLASSIFICATION", "TLP:CLEAR")
ASN_DATA_PATH = Path(os.environ.get("ASN_DATA_PATH", Path(__file__).with_name("asn.txt")))
TYPES = {"asn"}

logger = get_logger(__file__)


class AsnRecord(NamedTuple):
    """A parsed record from RIPE's ASN name dataset."""

    name: str
    country_code: str | None


def parse_asn_data(lines: list[str]) -> dict[int, AsnRecord]:
    """Parse RIPE ASN name records into a lookup indexed by ASN."""
    records: dict[int, AsnRecord] = {}

    for line_number, line in enumerate(lines, start=1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        try:
            asn_text, description = line.split(maxsplit=1)
            asn = int(asn_text)
        except ValueError:
            logger.warning("Ignoring malformed ASN record on line %s", line_number)
            continue

        name = description.strip()
        country_code: str | None = None
        description_parts = description.rsplit(",", maxsplit=1)
        if len(description_parts) == 2:
            possible_country = description_parts[1].strip()
            if re.fullmatch(r"[A-Z]{2}", possible_country):
                name = description_parts[0].strip()
                country_code = possible_country

        records[asn] = AsnRecord(name=name, country_code=country_code)

    return records


def load_asn_data(path: Path = ASN_DATA_PATH) -> dict[int, AsnRecord]:
    """Load the ASN dataset bundled into the plugin image."""
    try:
        with path.open(encoding="utf-8") as data_file:
            records = parse_asn_data(data_file.readlines())
    except OSError:
        logger.exception("Unable to load RIPE ASN data from %s", path)
        return {}

    logger.info("Loaded %s RIPE ASN name records from %s", len(records), path)
    return records


ASN_RECORDS = load_asn_data()


def normalize_asn(value: str) -> int | None:
    """Return the numeric portion of an ASN represented as `123` or `AS123`."""
    normalized = value.strip().upper()
    if normalized.startswith("AS"):
        normalized = normalized[2:]

    if not normalized.isdigit():
        return None

    try:
        asn = int(normalized)
    except ValueError:
        return None
    return asn if 0 <= asn <= 4_294_967_295 else None


def enrich(type_name: str, value: str, params: Params, token: str | None) -> QueryEntry:
    """Look up the RIPE name and country code for an ASN."""
    if type_name not in TYPES:
        raise InvalidDataException(f"Type name `{type_name}` is invalid. Valid types are: {', '.join(TYPES)}")

    result = QueryEntry(classification=CLASSIFICATION, count=0, annotations=[])
    asn = normalize_asn(value)
    if asn is None:
        return result

    record = ASN_RECORDS.get(asn)
    if record is None:
        return result

    result.count = 1
    canonical_asn = f"AS{asn}"
    location = f" ({record.country_code})" if record.country_code else ""
    if params.raw:
        result.raw_data = {
            "asn": asn,
            "name": record.name,
            "country_code": record.country_code,
            "source": "RIPE NCC ASN Names",
        }
    if params.annotate and params.limit > 0:
        result.annotations.append(
            Annotation(
                analytic="RIPE ASN Names",
                analytic_icon="carbon:network-3",
                icon="carbon:network-3",
                type="context",
                value=record.name,
                summary=f"{canonical_asn} is registered as {record.name}{location} in the RIPE ASN names dataset.",
                confidence=1.0,
            )
        )
    return result


plugin = CluePlugin(
    app_name=APP_NAME,
    classification=CLASSIFICATION,
    enrich=enrich,
    enable_cache=False,  # The dataset is already held in memory.
    supported_types=TYPES,
    logger=logger,
)
