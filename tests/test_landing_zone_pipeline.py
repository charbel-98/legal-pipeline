from datetime import date
from types import SimpleNamespace

from legal_pipeline.application.services.record_serializer import serialize_record
from legal_pipeline.domain.entities.record import DocumentRecord
from legal_pipeline.infrastructure.scrapy_project.object_naming import build_object_name
from legal_pipeline.infrastructure.scrapy_project.pipelines import LandingZonePipeline


def test_build_object_name_uses_stable_partitioned_path() -> None:
    object_name = build_object_name(
        source="workplace_relations",
        body="Labour Court",
        partition_date="2024-01-01",
        identifier="LCR22912",
        content_type="text/html",
        document_url="https://example.com/lcr22912.html",
    )

    assert object_name == "workplace_relations/labour_court/2024-01-01/lcr22912.html"


def test_build_object_name_uses_document_extension_for_binary_files() -> None:
    object_name = build_object_name(
        source="workplace_relations",
        body="Labour Court",
        partition_date="2024-01-01",
        identifier="DEC-E2001-001",
        content_type="application/pdf",
        file_name="full-case-report.pdf",
        document_url="https://example.com/files/full-case-report.pdf",
    )

    assert object_name == "workplace_relations/labour_court/2024-01-01/dec-e2001-001.pdf"


def test_serialize_record_converts_record_date_to_iso_string() -> None:
    record = DocumentRecord(
        source="workplace_relations",
        body="Labour Court",
        identifier="LCR22912",
        title="LCR22912",
        description=None,
        case_number="CD/24/11",
        record_date=date(2024, 1, 23),
        partition_date="2024-01-01",
        source_page_url="https://example.com/search",
        document_url="https://example.com/doc",
    )

    payload = serialize_record(record)

    assert payload["case_number"] == "CD/24/11"
    assert payload["record_date"] == "2024-01-23"


def test_landing_pipeline_marks_second_identical_item_as_unchanged() -> None:
    repository = FakeMetadataRepository()
    object_storage = FakeObjectStorage()
    pipeline = LandingZonePipeline(
        metadata_repository=repository,
        object_storage=object_storage,
        settings=SimpleNamespace(landing_retry_attempts=3, minio_landing_bucket="landing-zone"),
    )

    first = pipeline.process_item(build_item(identifier="LCR22912"))
    second = pipeline.process_item(build_item(identifier="LCR22912"))

    assert first["scrape_status"] == "stored"
    assert second["scrape_status"] == "unchanged"
    assert object_storage.upload_count == 1
    assert len(repository.records) == 1


def test_landing_pipeline_retries_transient_storage_failures() -> None:
    repository = FakeMetadataRepository()
    object_storage = FakeObjectStorage(fail_upload_attempts=2)
    pipeline = LandingZonePipeline(
        metadata_repository=repository,
        object_storage=object_storage,
        settings=SimpleNamespace(landing_retry_attempts=3, minio_landing_bucket="landing-zone"),
    )

    item = pipeline.process_item(build_item(identifier="LCR22913"))

    assert item["scrape_status"] == "stored"
    assert object_storage.upload_count == 3
    assert repository.records["workplace_relations:Labour Court:LCR22913"]["identifier"] == "LCR22913"


def test_landing_pipeline_uploads_binary_payloads_with_original_filename() -> None:
    repository = FakeMetadataRepository()
    object_storage = FakeObjectStorage()
    pipeline = LandingZonePipeline(
        metadata_repository=repository,
        object_storage=object_storage,
        settings=SimpleNamespace(landing_retry_attempts=3, minio_landing_bucket="landing-zone"),
    )

    item = pipeline.process_item(
        {
            **build_item(identifier="DEC-E2001-001"),
            "document_url": "https://example.com/files/full-case-report.pdf",
            "file_name": "full-case-report.pdf",
            "content_type": "application/pdf",
            "content_bytes": b"%PDF-1.7 fake payload",
            "content_html": None,
        }
    )

    assert item["scrape_status"] == "stored"
    assert object_storage.last_upload is not None
    assert object_storage.last_upload["object_name"].endswith("dec-e2001-001.pdf")
    assert object_storage.last_upload["payload"] == b"%PDF-1.7 fake payload"
    assert item["content_bytes"] is None
    assert repository.records["workplace_relations:Labour Court:DEC-E2001-001"]["file_name"] == "full-case-report.pdf"
    assert repository.records["workplace_relations:Labour Court:DEC-E2001-001"]["content_type"] == "application/pdf"


def build_item(identifier: str) -> dict[str, str]:
    return {
        "source": "workplace_relations",
        "body": "Labour Court",
        "identifier": identifier,
        "title": identifier,
        "description": "Example description",
        "case_number": "CD/24/11",
        "record_date": "2024-01-23",
        "partition_date": "2024-01-01",
        "source_page_url": "https://example.com/search",
        "document_url": f"https://example.com/{identifier.lower()}.html",
        "file_name": f"{identifier.lower()}.html",
        "content_type": "text/html",
        "content_bytes": None,
        "content_html": f"<div>{identifier}</div>",
    }


class FakeMetadataRepository:
    def __init__(self) -> None:
        self.records: dict[str, dict[str, str]] = {}

    def ensure_indexes(self) -> None:
        return None

    def upsert_landing_record(self, record: DocumentRecord) -> None:
        payload = serialize_record(record)
        key = self._build_key(record.source, record.body, record.identifier)
        self.records[key] = payload

    def upsert_processed_record(self, record: DocumentRecord) -> None:
        payload = serialize_record(record)
        key = self._build_key(record.source, record.body, record.identifier)
        self.records[key] = payload

    def find_landing_records_by_date_range(self, start_date: str, end_date: str) -> list[dict[str, str]]:
        return list(self.records.values())

    def get_landing_record(self, source: str, body: str, identifier: str) -> dict[str, str] | None:
        return self.records.get(self._build_key(source, body, identifier))

    def _build_key(self, source: str, body: str, identifier: str) -> str:
        return f"{source}:{body}:{identifier}"


class FakeObjectStorage:
    def __init__(self, fail_upload_attempts: int = 0) -> None:
        self.fail_upload_attempts = fail_upload_attempts
        self.upload_count = 0
        self.last_upload: dict[str, object] | None = None

    def upload_bytes(self, bucket_name: str, object_name: str, payload: bytes, content_type: str) -> str:
        self.upload_count += 1
        if self.upload_count <= self.fail_upload_attempts:
            raise RuntimeError("transient upload failure")
        self.last_upload = {
            "bucket_name": bucket_name,
            "object_name": object_name,
            "payload": payload,
            "content_type": content_type,
        }
        return f"{bucket_name}/{object_name}"

    def download_bytes(self, bucket_name: str, object_name: str) -> bytes:
        return b""
