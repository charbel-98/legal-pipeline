from abc import ABC, abstractmethod
from typing import Any

from legal_pipeline.domain.entities.record import DocumentRecord


class MetadataRepository(ABC):
    @abstractmethod
    def ensure_indexes(self) -> None:
        """Create indexes needed for idempotent access patterns."""

    @abstractmethod
    def upsert_landing_record(self, record: DocumentRecord) -> None:
        """Insert or update a landing-zone metadata record."""

    @abstractmethod
    def upsert_processed_record(self, record: DocumentRecord) -> None:
        """Insert or update a processed metadata record."""

    @abstractmethod
    def find_landing_records_by_date_range(
        self, start_date: str, end_date: str
    ) -> list[dict[str, Any]]:
        """Fetch landing-zone records for transformation."""

    @abstractmethod
    def get_landing_record(self, source: str, body: str, identifier: str) -> dict[str, Any] | None:
        """Fetch a single landing-zone record by stable identity."""
