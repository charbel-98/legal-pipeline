"""HTML cleaning — strips navigation chrome and extracts main case content."""

from __future__ import annotations

from bs4 import BeautifulSoup

_STRIP_TAGS = ["nav", "header", "footer", "script", "style", "noscript"]

_CONTENT_SELECTORS = [
    "article.case-detail",
    "div.case-content",
    "div#main-content",
    "div.content",
    "main",
]


def clean_html(raw: bytes) -> bytes:
    """Strip chrome from raw HTML bytes and return cleaned bytes."""
    soup = BeautifulSoup(raw, "html.parser")

    for tag_name in _STRIP_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    content_node = None
    for selector in _CONTENT_SELECTORS:
        results = soup.select(selector)
        if results:
            content_node = results[0]
            break

    serialized = str(content_node if content_node else soup.body or soup)
    return serialized.encode("utf-8")
