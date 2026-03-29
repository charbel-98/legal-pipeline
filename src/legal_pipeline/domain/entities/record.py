from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass(slots=True)
class DocumentRecord:
    source: str
    body: str
    identifier: str
    title: str
    description: Optional[str]
    record_date: Optional[date]
    partition_date: str
    source_page_url: str
    document_url: str
    content_type: Optional[str] = None
    storage_path: Optional[str] = None
    file_hash: Optional[str] = None
    scrape_status: str = "pending"

