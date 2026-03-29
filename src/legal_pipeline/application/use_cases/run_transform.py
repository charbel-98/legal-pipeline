from __future__ import annotations

from dataclasses import asdict
from datetime import date
from hashlib import sha256
from typing import Any

from legal_pipeline.application.config.settings import Settings, get_settings
from legal_pipeline.application.logging.logger import get_logger
from legal_pipeline.domain.entities.record import DocumentRecord
from legal_pipeline.domain.repositories.metadata_repository import MetadataRepository
from legal_pipeline.domain.storage.object_storage import ObjectStorage
from legal_pipeline.infrastructure.db.mongo_repository import MongoMetadataRepository
from legal_pipeline.infrastructure.object_store.minio_storage import MinioObjectStorage
from legal_pipeline.infrastructure.scrapy_project.object_naming import build_object_name, infer_extension
from legal_pipeline.infrastructure.transformers.html_cleaner import extract_relevant_html


def run_transform(
    start_date: str,
    end_date: str,
    metadata_repository: MetadataRepository | None = None,
    object_storage: ObjectStorage | None = None,
    settings: Settings | None = None,
) -> None:
    settings = settings or get_settings()
    metadata_repository = metadata_repository or MongoMetadataRepository(settings)
    object_storage = object_storage or MinioObjectStorage(settings)
    logger = get_logger(__name__)

    logger.info("transform_run_started", start_date=start_date, end_date=end_date)

    landing_records = metadata_repository.find_landing_records_by_date_range(start_date, end_date)
    transformed_count = 0
    passthrough_count = 0

    for landing_record in landing_records:
        processed_record = transform_record(
            landing_record=landing_record,
            object_storage=object_storage,
            settings=settings,
        )
        metadata_repository.upsert_processed_record(processed_record)

        if _is_html_content(processed_record.content_type):
            transformed_count += 1
        else:
            passthrough_count += 1

        logger.info(
            "transform_record_processed",
            identifier=processed_record.identifier,
            body=processed_record.body,
            content_type=processed_record.content_type,
            output_path=processed_record.storage_path,
        )

    logger.info(
        "transform_run_finished",
        start_date=start_date,
        end_date=end_date,
        records_read=len(landing_records),
        records_written=len(landing_records),
        transformed_count=transformed_count,
        passthrough_count=passthrough_count,
    )


def transform_record(
    landing_record: dict[str, Any],
    object_storage: ObjectStorage,
    settings: Settings,
) -> DocumentRecord:
    bucket_name, object_name = _split_storage_path(landing_record["storage_path"])
    original_payload = object_storage.download_bytes(bucket_name, object_name)
    content_type = landing_record.get("content_type") or "application/octet-stream"

    if _is_html_content(content_type):
        raw_html = original_payload.decode("utf-8")
        processed_html = extract_relevant_html(raw_html)
        processed_payload = processed_html.encode("utf-8")
        processed_content_type = "text/html"
    else:
        processed_payload = original_payload
        processed_content_type = content_type

    processed_file_name = _build_processed_file_name(
        identifier=landing_record["identifier"],
        content_type=processed_content_type,
        source_file_name=landing_record.get("file_name"),
        document_url=landing_record.get("document_url"),
    )
    processed_object_name = build_object_name(
        source=landing_record["source"],
        body=landing_record["body"],
        partition_date=landing_record["partition_date"],
        identifier=landing_record["identifier"],
        content_type=processed_content_type,
        file_name=processed_file_name,
        document_url=landing_record.get("document_url"),
    )
    storage_path = object_storage.upload_bytes(
        bucket_name=settings.minio_processed_bucket,
        object_name=processed_object_name,
        payload=processed_payload,
        content_type=processed_content_type,
    )

    return _build_processed_record(
        landing_record=landing_record,
        processed_file_name=processed_file_name,
        processed_content_type=processed_content_type,
        storage_path=storage_path,
        file_hash=sha256(processed_payload).hexdigest(),
    )


def _build_processed_record(
    landing_record: dict[str, Any],
    processed_file_name: str,
    processed_content_type: str,
    storage_path: str,
    file_hash: str,
) -> DocumentRecord:
    base_record = _normalize_record_payload(landing_record)
    record = DocumentRecord(**base_record)
    record.file_name = processed_file_name
    record.content_type = processed_content_type
    record.storage_path = storage_path
    record.file_hash = file_hash
    record.scrape_status = "transformed"
    return record


def _normalize_record_payload(landing_record: dict[str, Any]) -> dict[str, Any]:
    payload = {
        key: landing_record.get(key)
        for key in asdict(
            DocumentRecord(
                source="",
                body="",
                identifier="",
                title="",
                description=None,
                case_number=None,
                record_date=None,
                partition_date="",
                source_page_url="",
                document_url="",
            )
        ).keys()
    }
    payload["record_date"] = _parse_optional_date(payload.get("record_date"))
    return payload


def _parse_optional_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _is_html_content(content_type: str | None) -> bool:
    return bool(content_type and content_type.split(";", 1)[0].strip().lower() == "text/html")


def _split_storage_path(storage_path: str) -> tuple[str, str]:
    bucket_name, _, object_name = storage_path.partition("/")
    if not bucket_name or not object_name:
        raise ValueError(f"Invalid object storage path: {storage_path}")
    return bucket_name, object_name


def _build_processed_file_name(
    identifier: str,
    content_type: str | None,
    source_file_name: str | None,
    document_url: str | None,
) -> str:
    extension = infer_extension(
        content_type=content_type,
        file_name=source_file_name,
        document_url=document_url,
    )
    safe_identifier = identifier.lower().replace("/", "_")
    return f"{safe_identifier}.{extension}"
