"""Text a puzzle page holds but a reader would not see: found, and stripped before the prompt.

The parser hands a model the text of the puzzle's <article> elements (shared/parser.py,
BeautifulSoup get_text()), which would include text the browser does not display. A new page
could hold such text, by accident or by design. As registered (dev/progress/
aoc2026-registration.md, "Unseen pages, run unattended"), every reader of a cached page strips
it first (`strip_hidden`), so a model sees what a reader sees; and the audit (`audit_page`)
reports it, so the nightly run holds that day's submissions until the maintainer has read it.
The cached page itself is kept as AoC served it.

Found and stripped: elements hidden by inline style, the `hidden` attribute or aria-hidden;
HTML comments; invisible Unicode (zero-width and format characters, Unicode tag characters).
Found only: hover text (`title` attributes), which a reader sees on hover and get_text() leaves
out, so it never reaches the prompt. Stylesheet rules are not evaluated: a class hidden by CSS
is not detected.
"""

import re
import unicodedata
from dataclasses import dataclass
from typing import List

from bs4 import BeautifulSoup, Comment, Tag

_HIDING_STYLE = re.compile(
    r"display\s*:\s*none|visibility\s*:\s*hidden|font-size\s*:\s*0(?![.\d]*[1-9])"
    r"|opacity\s*:\s*0(?![.\d]*[1-9])|color\s*:\s*transparent",
    re.IGNORECASE,
)

# Kinds of finding. Hover text is reported but is ordinary on AoC pages.
HIDDEN_ELEMENT = "hidden element"
COMMENT = "comment"
INVISIBLE_CHARACTER = "invisible character"
HOVER_TEXT = "hover text"


@dataclass(frozen=True)
class Finding:
    kind: str
    text: str

    def line(self) -> str:
        shown = self.text if len(self.text) <= 120 else self.text[:117] + "..."
        return f"{self.kind}: {shown!r}"


def _invisible(char: str) -> bool:
    """Format characters (zero-width space and joiners, bidi controls, BOM) and tags."""
    return unicodedata.category(char) == "Cf" or 0xE0000 <= ord(char) <= 0xE007F


def audit_page(html: str) -> List[Finding]:
    """Everything in the page's puzzle articles that a reader would not see as text."""
    soup = BeautifulSoup(html, "html.parser")
    articles = _articles(soup)
    findings: List[Finding] = []
    for article in articles:
        for element in article.find_all(True):
            if not isinstance(element, Tag):
                continue
            if _hidden(element):
                findings.append(Finding(HIDDEN_ELEMENT, " ".join(element.get_text().split())))
            if element.has_attr("title"):
                findings.append(Finding(HOVER_TEXT, str(element["title"])))
        for comment in article.find_all(string=lambda s: isinstance(s, Comment)):
            findings.append(Finding(COMMENT, str(comment).strip()))
        invisible = sorted({c for c in article.get_text() if _invisible(c)})
        for char in invisible:
            findings.append(Finding(INVISIBLE_CHARACTER, f"U+{ord(char):04X} {unicodedata.name(char, '')}".strip()))
    return findings


def _hidden(element: Tag) -> bool:
    return bool(_HIDING_STYLE.search(str(element.get("style", ""))) or element.has_attr("hidden")
                or str(element.get("aria-hidden", "")).lower() == "true")


def _articles(soup: BeautifulSoup) -> List[Tag]:
    found = soup.find_all("article", class_="day-desc") or soup.find_all("article")
    return [article for article in found if isinstance(article, Tag)]


def strip_hidden(soup: BeautifulSoup) -> BeautifulSoup:
    """Remove from the puzzle articles, in place, everything `audit_page` reports but hover
    text: hidden elements, comments and invisible characters. Returns `soup`."""
    for article in _articles(soup):
        for element in article.find_all(True):
            if isinstance(element, Tag) and not element.decomposed and _hidden(element):
                element.decompose()
        for comment in article.find_all(string=lambda s: isinstance(s, Comment)):
            comment.extract()
        for text in article.find_all(string=True):
            if any(_invisible(c) for c in text):
                text.replace_with("".join(c for c in text if not _invisible(c)))
    return soup


def needs_review(findings: List[Finding]) -> bool:
    """Whether a page holds anything beyond hover text, so its day is reported apart."""
    return any(f.kind != HOVER_TEXT for f in findings)
