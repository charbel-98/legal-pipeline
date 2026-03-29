from dataclasses import dataclass
from datetime import date


@dataclass(slots=True)
class DocumentRecord:
    source: str
    body: str
    identifier: str
    title: str
    description: str | None
    case_number: str | None
    record_date: date | None
    partition_date: str
    source_page_url: str
    document_url: str
    file_name: str | None = None
    content_type: str | None = None
    storage_path: str | None = None
    file_hash: str | None = None
    scrape_status: str = "pending"
