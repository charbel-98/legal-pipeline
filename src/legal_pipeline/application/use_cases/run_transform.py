from __future__ import annotations

from dataclasses import fields as dataclass_fields
from typing import Any

from legal_pipeline.application.config.settings import Settings, get_settings
from legal_pipeline.application.logging.logger import get_logger
from legal_pipeline.application.services.date_utils import parse_optional_date
from legal_pipeline.application.services.hash_service import sha256_bytes
from legal_pipeline.domain.entities.record import DocumentRecord
from legal_pipeline.domain.entities.scrape_status import ScrapeStatus
from legal_pipeline.domain.repositories.metadata_repository import MetadataRepository
from legal_pipeline.domain.storage.object_storage import ObjectStorage
from legal_pipeline.infrastructure.scrapy_project.object_naming import (
    build_object_name,
    infer_extension,
)
from legal_pipeline.infrastructure.transformers.html_cleaner import extract_relevant_html


def run_transform(
    start_date: str,
    end_date: str,
    metadata_repository: MetadataRepository,
    object_storage: ObjectStorage,
    settings: Settings | None = None,
) -> None:
    settings = settings or get_settings()
    logger = get_logger(__name__)

    logger.info("transform_run_started", start_date=start_date, end_date=end_date)

    landing_records = metadata_repository.find_landing_records_by_date_range(start_date, end_date)
    transformed_count = 0
    passthrough_count = 0
    total_records = 0

    for landing_record in landing_records:
        total_records += 1
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
            output_path=processed_record.path_to_file,
        )

    logger.info(
        "transform_run_finished",
        start_date=start_date,
        end_date=end_date,
        records_read=total_records,
        records_written=total_records,
        transformed_count=transformed_count,
        passthrough_count=passthrough_count,
    )


def transform_record(
    landing_record: dict[str, Any],
    object_storage: ObjectStorage,
    settings: Settings,
) -> DocumentRecord:
    bucket_name, object_name = _split_storage_path(landing_record["path_to_file"])
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
        link_to_doc=landing_record.get("link_to_doc"),
    )
    processed_object_name = build_object_name(
        source=landing_record["source"],
        body=landing_record["body"],
        partition_date=landing_record["partition_date"],
        identifier=landing_record["identifier"],
        content_type=processed_content_type,
        file_name=processed_file_name,
        document_url=landing_record.get("link_to_doc"),
    )
    path_to_file = object_storage.upload_bytes(
        bucket_name=settings.minio_processed_bucket,
        object_name=processed_object_name,
        payload=processed_payload,
        content_type=processed_content_type,
    )

    return _build_processed_record(
        landing_record=landing_record,
        processed_file_name=processed_file_name,
        processed_content_type=processed_content_type,
        path_to_file=path_to_file,
        file_hash=sha256_bytes(processed_payload),
    )


def _build_processed_record(
    landing_record: dict[str, Any],
    processed_file_name: str,
    processed_content_type: str,
    path_to_file: str,
    file_hash: str,
) -> DocumentRecord:
    base_record = _normalize_record_payload(landing_record)
    record = DocumentRecord(**base_record)
    record.file_name = processed_file_name
    record.content_type = processed_content_type
    record.path_to_file = path_to_file
    record.file_hash = file_hash
    record.scrape_status = ScrapeStatus.TRANSFORMED
    return record


def _normalize_record_payload(landing_record: dict[str, Any]) -> dict[str, Any]:
    payload = {f.name: landing_record.get(f.name) for f in dataclass_fields(DocumentRecord)}
    payload["record_date"] = parse_optional_date(payload.get("record_date"))
    return payload


def _is_html_content(content_type: str | None) -> bool:
    return bool(content_type and content_type.split(";", 1)[0].strip().lower() == "text/html")


def _split_storage_path(path_to_file: str) -> tuple[str, str]:
    bucket_name, _, object_name = path_to_file.partition("/")
    if not bucket_name or not object_name:
        raise ValueError(f"Invalid object storage path: {path_to_file}")
    return bucket_name, object_name


def _build_processed_file_name(
    identifier: str,
    content_type: str | None,
    source_file_name: str | None,
    link_to_doc: str | None,
) -> str:
    extension = infer_extension(
        content_type=content_type,
        file_name=source_file_name,
        document_url=link_to_doc,
    )
    safe_identifier = identifier.lower().replace("/", "_")
    return f"{safe_identifier}.{extension}"
