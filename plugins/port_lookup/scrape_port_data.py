import json
import re
from datetime import datetime
from pathlib import Path
from typing import cast

import requests
from bs4 import BeautifulSoup, Tag
from markdownify import markdownify

article_file = Path(__file__).parent / "article.html"
if not article_file.exists():
    response = requests.get("https://en.wikipedia.org/wiki/List_of_TCP_and_UDP_port_numbers", timeout=10)
    article_file.write_text(response.text)

bs = BeautifulSoup(article_file.read_text(), "html.parser")

body = cast(Tag, bs.find("div", {"id": "bodyContent"}))

for citation in body.find_all("sup", {"class": "reference"}):
    citation.decompose()

for citation_needed in body.find_all("sup", {"class": "noprint"}):
    citation_needed.decompose()

tables = cast(list[Tag], body.find_all("table", {"class": "wikitable sortable collapsible"}))

docpage = Path(__file__).parent / "summary.md"

rows: list[dict[str, int | str]] = []
with docpage.open("w") as _doc:
    _doc.write("# Summary of port uses\n\n")

    for link in body.find_all("a"):
        href = cast(str, cast(Tag, link).get("href"))
        if not href:
            link.decompose()
            continue

        if href.startswith("#"):
            link.decompose()
            continue

        if href.startswith("/wiki"):
            cast(Tag, link)["href"] = "https://en.wikipedia.org" + href

    for table in tables:
        port_range: tuple[int, int] = cast(tuple[int, int], None)
        for row in cast(Tag, table.find("tbody")).find_all("tr"):
            cells = cast(Tag, row).find_all("td")

            if len(cells) == 0:
                continue

            first, last = cells[0], cast(Tag, cells[-1])

            port_candidate = first.get_text(strip=True).strip()
            if port_candidate and len(re.sub(r"[^\d]+", "", port_candidate.strip())) > 0:
                try:
                    port_range = cast(
                        tuple[int, int],
                        tuple(int(item) for item in re.sub(r"[^\d]+", " ", port_candidate.strip()).split()),
                    )
                except ValueError:
                    pass

            if len(port_range) < 2:
                port_range = (port_range[0], port_range[0])

            if "unofficial" in row.get_text(strip=True).lower():
                unofficial = " <strong>(Unofficial use)</strong>"
            else:
                unofficial = ""

            md = markdownify("".join(str(item) for item in last.contents).strip() + unofficial)

            _doc.write(f"- {port_range[0]} TO {port_range[1]}: {md}\n")
            rows.append(
                {
                    "start": port_range[0],
                    "end": port_range[1],
                    "value": last.get_text(strip=True, separator=" "),
                    "summary": md,
                    "timestamp": datetime.now().isoformat(),
                }
            )

data_file = Path(__file__).parent / "data.json"

with data_file.open("w") as _f:
    json.dump(rows, _f, indent=2)
