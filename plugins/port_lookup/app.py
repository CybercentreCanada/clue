"""Port Lookup Plugin

Status: In Development

Provides context on common uses for ports.
"""

import os
from typing import Optional
from urllib.parse import urlsplit

import iana_ports
import wikipedia_data
from clue.common.exceptions import InvalidDataException
from clue.common.logging import get_logger
from clue.models.network import QueryEntry
from clue.plugin import CluePlugin
from clue.plugin.utils import Params

CLASSIFICATION = os.environ.get("CLASSIFICATION", "TLP:CLEAR")

logger = get_logger(__file__)

TYPES = {"port", "url"}

PORT_NUMBERS = iana_ports.read_port_annotations()

PORT_ICONS = {
    20: "arcticons:totalcmd-ftp",  # FTP
    21: "arcticons:totalcmd-ftp",  # FTP
    22: "mdi:ssh",  # SSH
    23: "material-symbols:terminal",  # Telnet
    25: "ic:baseline-email",  # SMTP
    53: "iconoir:dns",  # DNS
    67: "mdi:ip",  # DHCP
    68: "mdi:ip",  # DHCP
    80: "material-symbols:http",  # HTTP
    110: "ic:baseline-email",  # POP3
    123: "carbon:time",  # NTP
    143: "ic:baseline-email",  # IMAP
    194: "arcticons:irc",  # IRC
    389: "hugeicons:login-method",  # LDAP
    443: "ic:baseline-https",  # HTTPS
    464: "hugeicons:login-method",  # Kerberos
    465: "ic:baseline-email",  # SMTP over SSL
    546: "mdi:ip",  # DHCP
    547: "mdi:ip",  # DHCP
    554: "mdi:video",  # RTSP
    587: "ic:baseline-email",  # SMTP
    631: "material-symbols:print",  # IPP
    636: "hugeicons:login-method",  # LDAP over TLS
    691: "ic:baseline-email",  # Microsoft Exchange
    860: "material-symbols:hard-disk",  # iSCSI
    989: "arcticons:totalcmd-ftp",  # FTPs
    990: "arcticons:totalcmd-ftp",  # FTPs
    993: "ic:baseline-email",  # IMAP over SSL
    995: "ic:baseline-email",  # POP3 over SSL
    3260: "material-symbols:hard-disk",  # iSCSI Target Server
    3306: "tabler:sql",  # MySQL
    5432: "tabler:sql",  # Postgres
    8080: "material-symbols:http",  # HTTP Alt
    8443: "ic:baseline-https",  # HTTPS Alt
}


plugin = CluePlugin(
    app_name=os.environ.get("APP_NAME", "port-lookup"),
    classification=CLASSIFICATION,
    enable_apm=False,
    enable_cache=False,  # Not necessary given this already sits in memory
    supported_types=TYPES,
    logger=logger,
)


def _parse_port_from_domain(domain: str) -> Optional[int]:
    split_domain = domain.split(":")
    if len(split_domain) == 2:
        return int(split_domain[1])
    else:
        logger.warning(f"Invalid domain for port lookup: {domain}")
        return None


@plugin.use
def enrich(type_name: str, value: str, params: Params, *_args) -> QueryEntry:
    "Enrich a given indicator"
    if type_name not in TYPES:
        raise InvalidDataException(message=f"Type name `{type_name}` is invalid. Valid types are: {', '.join(TYPES)}")

    port: Optional[int] = None

    if type_name == "url":
        # Extract the netloc from the URL (domain + optional port) and then extract the port if available
        port = _parse_port_from_domain(urlsplit(value).netloc)
    else:  # port
        try:
            port = int(value)
        except ValueError:
            raise InvalidDataException("Unable to interpret port as number")

    if port is None:
        # Value doesn't contain a valid port, but isn't necessarily invalid as could be a domain without a port
        return QueryEntry(classification=CLASSIFICATION, count=0)

    logger.info(f"Enriching [{type_name}] {value} -> :{port} limit {params.limit} (annotate={params.annotate})")

    port_data = PORT_NUMBERS.get(port, [])

    if len(port_data) < 1:
        port_data = wikipedia_data.fetch_port_information(port)

    # Enrich with icons
    for annotation in port_data:
        annotation.icon = PORT_ICONS.get(port, None)

    result = QueryEntry(
        classification=CLASSIFICATION,
        count=len(port_data),
        annotations=port_data[0 : params.limit],
    )

    return result
