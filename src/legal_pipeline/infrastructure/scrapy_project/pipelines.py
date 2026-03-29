from typing import Any

try:
    from scrapy.exceptions import DropItem
except ModuleNotFoundError:  # pragma: no cover - used only in lightweight unit tests

    class DropItem(Exception):
        pass


from legal_pipeline.application.services.date_utils import parse_optional_date
from legal_pipeline.application.services.hash_service import sha256_bytes
from legal_pipeline.domain.entities.record import DocumentRecord
from legal_pipeline.domain.entities.scrape_status import ScrapeStatus
from legal_pipeline.domain.repositories.metadata_repository import MetadataRepository
from legal_pipeline.domain.storage.object_storage import ObjectStorage
from legal_pipeline.infrastructure.scrapy_project.object_naming import build_object_name


class LandingZonePipeline:
    def __init__(
        self,
        metadata_repository: MetadataRepository | None = None,
        object_storage: ObjectStorage | None = None,
        settings: Any | None = None,
    ) -> None:
        if settings is None:
            from legal_pipeline.application.config.settings import get_settings

            settings = get_settings()
        self._settings = settings
        if metadata_repository is None:
            from legal_pipeline.infrastructure.db.mongo_repository import MongoMetadataRepository

            metadata_repository = MongoMetadataRepository(self._settings)
        if object_storage is None:
            from legal_pipeline.infrastructure.object_store.minio_storage import MinioObjectStorage

            object_storage = MinioObjectStorage(self._settings)
        self._metadata_repository = metadata_repository
        self._object_storage = object_storage
        self._crawler: Any | None = None

    @classmethod
    def from_crawler(cls, crawler: Any) -> "LandingZonePipeline":
        pipeline = cls()
        pipeline._crawler = crawler
        return pipeline

    def process_item(self, item: Any) -> Any:
        try:
            return self._process_item(item)
        except Exception as exc:
            self._inc_stat("landing_pipeline/failed")
            identifier = str(item.get("identifier") or "unknown")
            source = str(item.get("source") or "unknown")
            link_to_doc = str(item.get("link_to_doc") or "unknown")
            if self._crawler is not None:
                self._crawler.spider.logger.error(
                    "landing_pipeline_failed",
                    extra={
                        "identifier": identifier,
                        "source": source,
                        "link_to_doc": link_to_doc,
                        "error": str(exc),
                    },
                )
            raise DropItem(f"Failed to persist landing item {source}:{identifier}: {exc}") from exc

    def _process_item(self, item: Any) -> Any:
        payload = self._build_payload(item)
        file_hash = sha256_bytes(payload)

        source = str(item["source"])
        body = str(item.get("body") or "unknown")
        identifier = str(item["identifier"])
        existing = self._metadata_repository.get_landing_record(
            source=source,
            body=body,
            identifier=identifier,
        )

        if existing and existing.get("file_hash") == file_hash and existing.get("path_to_file"):
            path_to_file = str(existing["path_to_file"])
            scrape_status = ScrapeStatus.UNCHANGED
            self._inc_stat("landing_pipeline/unchanged")
        else:
            object_name = build_object_name(
                source=source,
                body=body,
                partition_date=str(item["partition_date"]),
                identifier=identifier,
                content_type=str(item.get("content_type") or "text/html"),
                file_name=_optional_str(item.get("file_name")),
                document_url=_optional_str(item.get("link_to_doc")),
            )
            path_to_file = self._with_retries(
                operation_name="upload_bytes",
                func=self._object_storage.upload_bytes,
                bucket_name=self._settings.minio_landing_bucket,
                object_name=object_name,
                payload=payload,
                content_type=str(item.get("content_type") or "text/html"),
            )
            scrape_status = ScrapeStatus.STORED
            self._inc_stat("landing_pipeline/stored")

        record = DocumentRecord(
            source=source,
            body=body,
            identifier=identifier,
            title=str(item.get("title") or identifier),
            description=_optional_str(item.get("description")),
            case_number=_optional_str(item.get("case_number")),
            record_date=parse_optional_date(item.get("record_date")),
            partition_date=str(item["partition_date"]),
            source_page_url=str(item["source_page_url"]),
            link_to_doc=str(item["link_to_doc"]),
            file_name=_optional_str(item.get("file_name")),
            content_type=str(item.get("content_type") or "text/html"),
            path_to_file=path_to_file,
            file_hash=file_hash,
            scrape_status=scrape_status,
        )
        self._with_retries(
            operation_name="upsert_landing_record",
            func=self._metadata_repository.upsert_landing_record,
            record=record,
        )

        item["path_to_file"] = path_to_file
        item["file_hash"] = file_hash
        item["scrape_status"] = scrape_status
        if item.get("content_bytes") is not None:
            item["content_bytes"] = None
        return item

    def _build_payload(self, item: Any) -> bytes:
        if item.get("content_bytes"):
            payload = item["content_bytes"]
            if isinstance(payload, bytes):
                return payload
            return bytes(payload)
        if item.get("content_html"):
            return str(item["content_html"]).encode("utf-8")
        return str(item.get("link_to_doc") or "").encode("utf-8")

    def _with_retries(self, operation_name: str, func: Any, **kwargs: Any) -> Any:
        last_error: Exception | None = None
        attempts = max(int(self._settings.landing_retry_attempts), 1)
        for attempt in range(1, attempts + 1):
            try:
                return func(**kwargs)
            except Exception as exc:  # pragma: no cover - exercised via tests with fakes
                last_error = exc
                if attempt == attempts:
                    break
                self._inc_stat("landing_pipeline/retries")
                if self._crawler is not None:
                    self._crawler.spider.logger.warning(
                        "landing_pipeline_retry",
                        extra={
                            "operation": operation_name,
                            "attempt": attempt,
                            "max_attempts": attempts,
                            "error": str(exc),
                        },
                    )
        assert last_error is not None
        raise last_error

    def _inc_stat(self, key: str) -> None:
        if self._crawler is not None:
            self._crawler.stats.inc_value(key)


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None
