"""Scrapy-layer metadata model — maps spider output to MongoDB document shape."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CaseMetadata:
    """Represents the metadata stored in MongoDB for a single scraped case."""

    identifier: str
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
    scraped_at: str  # ISO 8601 UTC
    file_name: str = ""
