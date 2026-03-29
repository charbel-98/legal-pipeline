"""Shared in-memory test doubles for MetadataRepository and ObjectStorage."""
from __future__ import annotations

from typing import Any

from legal_pipeline.application.services.record_serializer import serialize_record
from legal_pipeline.domain.entities.record import DocumentRecord


class FakeMetadataRepository:
    """In-memory metadata repository for use in unit tests.

    Supports both the landing-pipeline (upsert + get) and transform-pipeline
    (find by date range + upsert processed) access patterns.

    Pass ``landing_records`` to pre-seed the records returned by
    ``find_landing_records_by_date_range``; otherwise the repository returns
    whatever has been upserted via ``upsert_landing_record``.
    """

    def __init__(self, landing_records: list[dict[str, Any]] | None = None) -> None:
        self._seeded_landing: list[dict[str, Any]] = landing_records or []
        self.records: dict[str, dict[str, Any]] = {}
        self.processed_records: dict[str, dict[str, Any]] = {}

    def ensure_indexes(self) -> None:
        pass

    def upsert_landing_record(self, record: DocumentRecord) -> None:
        key = self._key(record.source, record.body, record.identifier)
        self.records[key] = serialize_record(record)

    def upsert_processed_record(self, record: DocumentRecord) -> None:
        key = self._key(record.source, record.body, record.identifier)
        self.processed_records[key] = serialize_record(record)

    def find_landing_records_by_date_range(
        self, start_date: str, end_date: str
    ) -> list[dict[str, Any]]:
        if self._seeded_landing:
            return list(self._seeded_landing)
        return list(self.records.values())

    def get_landing_record(
        self, source: str, body: str, identifier: str
    ) -> dict[str, Any] | None:
        return self.records.get(self._key(source, body, identifier))

    @staticmethod
    def _key(source: str, body: str, identifier: str) -> str:
        return f"{source}:{body}:{identifier}"


class FakeObjectStorage:
    """In-memory object storage for use in unit tests.

    Pass ``objects`` to pre-seed downloadable content.
    Use ``fail_upload_attempts`` to simulate transient upload failures.
    """

    def __init__(
        self,
        objects: dict[str, bytes] | None = None,
        fail_upload_attempts: int = 0,
    ) -> None:
        self.objects: dict[str, bytes] = dict(objects or {})
        self.fail_upload_attempts = fail_upload_attempts
        self.upload_count = 0
        self.last_upload: dict[str, Any] | None = None
        self.uploads: list[dict[str, Any]] = []

    def upload_bytes(
        self, bucket_name: str, object_name: str, payload: bytes, content_type: str
    ) -> str:
        self.upload_count += 1
        if self.upload_count <= self.fail_upload_attempts:
            raise RuntimeError("transient upload failure")
        entry: dict[str, Any] = {
            "bucket_name": bucket_name,
            "object_name": object_name,
            "payload": payload,
            "content_type": content_type,
        }
        self.uploads.append(entry)
        self.last_upload = entry
        self.objects[f"{bucket_name}/{object_name}"] = payload
        return f"{bucket_name}/{object_name}"

    def download_bytes(self, bucket_name: str, object_name: str) -> bytes:
        return self.objects[f"{bucket_name}/{object_name}"]
