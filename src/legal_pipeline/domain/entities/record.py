from dataclasses import dataclass
from datetime import date

from legal_pipeline.domain.entities.scrape_status import ScrapeStatus


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
    link_to_doc: str
    file_name: str | None = None
    content_type: str | None = None
    path_to_file: str | None = None
    file_hash: str | None = None
    scrape_status: str = ScrapeStatus.PENDING
