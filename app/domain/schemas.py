"""TypedDict schemas matching the MongoDB document shape."""

from __future__ import annotations

from typing import Required, TypedDict


class LandingDocument(TypedDict, total=False):
    identifier: Required[str]
    source: str
    body: str
    title: str
    description: str
    case_number: str
    record_date: str
    partition_date: str
    source_page_url: str
    link_to_doc: str
    content_type: str
    path_to_file: str
    file_hash: str
    scraped_at: str  # ISO 8601


class CuratedDocument(LandingDocument, total=False):
    processed_at: str  # ISO 8601
