"""
Pure HTML parsing functions for the WRC legal cases scraper.

All functions are stateless — they take a scrapy.http.Response (read-only)
and return primitives or LegalCaseItem objects. No I/O, no side-effects.
This makes them trivially unit-testable without a running Scrapy engine.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

import scrapy.http

from legal_scraper.items import LegalCaseItem

# MIME types that indicate a binary file that should be stored as-is
_BINARY_MIME_TYPES: frozenset[str] = frozenset(
    [
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-word.document.macroenabled.12",
    ]
)

# Ordered list of CSS selectors to find the main case content node
_CONTENT_SELECTORS: list[str] = [
    "article.case-detail",
    "div.case-content",
    "div#main-content",
    "div.content",
    "main",
]

# CSS / XPath selectors to find a linked attachment (PDF/DOC)
_ATTACHMENT_CSS_SELECTORS: list[str] = [
    "div.content a[href$='.pdf']::attr(href)",
    "div.content a[href$='.doc']::attr(href)",
    "div.content a[href$='.docx']::attr(href)",
    "div.related-items.related-file a.download::attr(href)",
    "div.related-item-content a.download::attr(href)",
]

_ATTACHMENT_XPATH_SELECTORS: list[str] = [
    (
        "//div[contains(@class,'content')]"
        "//a[contains(translate(normalize-space(.),"
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),"
        "'full case report')]/@href"
    ),
    (
        "//div[contains(@class,'content')]"
        "//a[contains(@href,'.pdf') or contains(@href,'.doc')]/@href"
    ),
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def normalize_content_type(raw: bytes | str | None) -> str:
    """Return the bare MIME type from a raw Content-Type header value.

    Examples:
        b"text/html; charset=utf-8"  →  "text/html"
        "application/pdf"            →  "application/pdf"
        None                         →  ""
    """
    if not raw:
        return ""
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="ignore")
    return raw.split(";")[0].strip().lower()


def is_download_response(response: scrapy.http.Response) -> bool:
    """Return True when the response is a binary file (PDF, DOC, etc.)."""
    content_type = normalize_content_type(response.headers.get("Content-Type"))
    if content_type in _BINARY_MIME_TYPES:
        return True
    path = urlparse(response.url).path.lower()
    return path.endswith((".pdf", ".doc", ".docx"))


def extract_attachment_href(response: scrapy.http.Response) -> str | None:
    """Scan the page for a linked PDF/DOC attachment.

    Returns the raw href string (caller must urljoin) or None if not found.
    """
    for selector in _ATTACHMENT_CSS_SELECTORS:
        href = response.css(selector).get()
        if href:
            return href
    for selector in _ATTACHMENT_XPATH_SELECTORS:
        href = response.xpath(selector).get()
        if href:
            return href
    return None


def extract_content_html(response: scrapy.http.Response) -> str:
    """Return the outer HTML of the main content node, or an empty string."""
    for selector in _CONTENT_SELECTORS:
        node = response.css(selector).get(default="")
        if node:
            return node
    return ""


def extract_content_text(response: scrapy.http.Response) -> str:
    """Return cleaned plain text from the main content node."""
    for selector in _CONTENT_SELECTORS:
        parts = response.css(f"{selector} ::text").getall()
        if parts:
            return _clean_text(" ".join(parts))
    return ""


def has_meaningful_html_content(response: scrapy.http.Response) -> bool:
    """Return True when the page contains extractable case text (≥100 chars)."""
    if not extract_content_html(response):
        return False
    return len(extract_content_text(response)) >= 100


def build_item_from_html(
    response: scrapy.http.Response,
    partial_item: LegalCaseItem,
) -> LegalCaseItem:
    """Build a complete LegalCaseItem from an HTML case detail page."""
    item = _copy_partial_item(partial_item)
    item["content_type"] = normalize_content_type(response.headers.get("Content-Type")) or "text/html"
    item["content_html"] = extract_content_html(response)
    item["content_bytes"] = None
    item["link_to_doc"] = response.url
    return item


def build_item_from_file(
    response: scrapy.http.Response,
    partial_item: LegalCaseItem,
) -> LegalCaseItem:
    """Build a complete LegalCaseItem from a binary file response (PDF/DOC)."""
    item = _copy_partial_item(partial_item)
    item["content_type"] = (
        normalize_content_type(response.headers.get("Content-Type")) or "application/octet-stream"
    )
    item["content_bytes"] = response.body
    item["content_html"] = None
    item["link_to_doc"] = response.url
    return item


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _clean_text(text: str) -> str:
    """Collapse runs of whitespace and strip leading/trailing whitespace."""
    return re.sub(r"\s+", " ", text).strip()


def _copy_partial_item(partial_item: LegalCaseItem) -> LegalCaseItem:
    """Return a new LegalCaseItem with all currently set fields copied over."""
    item = LegalCaseItem()
    for field in partial_item.fields:
        if field in partial_item:
            item[field] = partial_item[field]
    return item
