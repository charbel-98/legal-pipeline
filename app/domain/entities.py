"""Domain entities representing records at each pipeline stage."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class LandingRecord:
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
    scraped_at: datetime = field(default_factory=datetime.utcnow)
    file_name: str = ""


@dataclass
class CuratedRecord(LandingRecord):
    processed_at: datetime = field(default_factory=datetime.utcnow)
