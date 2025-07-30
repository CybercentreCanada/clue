from pathlib import Path

from bs4 import BeautifulSoup

from clue.plugin.helpers.email_render import filter_elements

BAD_HTML = (Path(__file__).parent / "bad.html").read_text()
GOOD_HTML = (Path(__file__).parent / "good.html").read_text()


def test_filter_elements():
    assert filter_elements(BAD_HTML) == BeautifulSoup(GOOD_HTML, "html.parser").prettify()
