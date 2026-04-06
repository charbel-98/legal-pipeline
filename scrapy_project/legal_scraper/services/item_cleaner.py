"""Cleans and normalises a raw LegalCaseItem before it is persisted.

The spider is responsible only for extracting raw values from the page.
All normalisation — whitespace collapsing, empty-to-None coercion,
identifier resolution, date formatting — lives here so it is testable
independently of Scrapy.
"""

from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import urlparse


def clean_item(item) -> None:
    """Mutate *item* in-place: clean all string fields and resolve identifier."""
    # --- Normalise every string field ---
    for field in ("title", "description", "case_number", "record_date", "source", "body"):
        item[field] = _clean_text(item.get(field))

    # --- Resolve the best available identifier ---
    item["identifier"] = _resolve_identifier(
        raw_identifier=_clean_text(item.get("identifier")),
        source_page_url=item.get("source_page_url") or "",
        title=item.get("title"),
    )

    # --- Normalise record_date to ISO (YYYY-MM-DD) if given as DD/MM/YYYY ---
    item["record_date"] = _normalise_date(item.get("record_date"))


# ---------------------------------------------------------------------------
# Identifier resolution
# ---------------------------------------------------------------------------


def _resolve_identifier(
    raw_identifier: str | None,
    source_page_url: str,
    title: str | None,
) -> str | None:
    """Return the best identifier for a case.

    Priority:
    1. raw_identifier from span.refNO — unless it is purely numeric (not a
       real case reference), in which case the URL slug is more reliable.
    2. Slug derived from the URL path  (e.g. ADJ-00012345).
    3. Title as a last resort.
    """
    slug = _identifier_from_url(source_page_url)
    if not raw_identifier:
        return slug or title
    if raw_identifier.isdigit() and slug:
        return slug
    return raw_identifier or slug or title


def _identifier_from_url(url: str) -> str | None:
    """Extract a case-reference slug from the last path segment of a URL.

    /en/decisions/2024/ADJ-00012345  →  ADJ-00012345
    /en/decisions/2024/report.pdf    →  REPORT  (stem, uppercased)
    """
    if not url:
        return None
    name = urlparse(url).path.rsplit("/", 1)[-1]
    stem = name.rsplit(".", 1)[0].strip().upper()
    return stem or None


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------


def _clean_text(value: str | None) -> str | None:
    """Collapse whitespace runs and strip; return None for blank strings."""
    if value is None:
        return None
    cleaned = re.sub(r"\s+", " ", str(value)).strip()
    return cleaned or None


def _normalise_date(value: str | None) -> str | None:
    """Convert DD/MM/YYYY → YYYY-MM-DD; pass through values already in ISO form."""
    if not value:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    # Unrecognised format — return as-is so we don't silently discard it
    return value
