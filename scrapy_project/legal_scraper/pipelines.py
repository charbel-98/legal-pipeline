import logging
from datetime import datetime, timezone

import pymongo
from scrapy import Spider
from scrapy.exceptions import DropItem

from app.repositories.landing_metadata_repository import LandingMetadataRepository
from app.repositories.metadata_repository import MetadataRepository
from app.storage.minio_store import MinioStore
from app.storage.object_store import ObjectStore
from app.utils.hashing import sha256_of_bytes
from legal_scraper.services.item_cleaner import clean_item
from legal_scraper.services.object_naming import build_object_key

logger = logging.getLogger(__name__)

_DEFAULT_RETRY_ATTEMPTS = 3


class LandingZonePipeline:
    """
    Persists scraped items to the landing zone (MinIO + MongoDB).

    Dedup logic: checks MongoDB first. If the existing record has the same
    file_hash and a path_to_file, the upload is skipped entirely (cheaper
    than hitting MinIO on every item). MinIO is only contacted when content
    has actually changed or is new.

    Idempotent: running the same date range twice produces the same state.
    """

    def __init__(
        self,
        object_store: ObjectStore,
        metadata_repo: MetadataRepository,
        retry_attempts: int = _DEFAULT_RETRY_ATTEMPTS,
    ) -> None:
        self._store = object_store
        self._repo = metadata_repo
        self._retry_attempts = retry_attempts
        self._crawler = None

    @classmethod
    def from_crawler(cls, crawler):
        settings = crawler.settings
        endpoint = f"{settings.get('MINIO_HOST')}:{settings.getint('MINIO_PORT')}"
        store = MinioStore(
            endpoint=endpoint,
            access_key=settings.get("MINIO_ROOT_USER"),
            secret_key=settings.get("MINIO_ROOT_PASSWORD"),
            bucket=settings.get("MINIO_LANDING_BUCKET"),
        )
        mongo_client = pymongo.MongoClient(
            host=settings.get("MONGO_HOST"),
            port=settings.getint("MONGO_PORT"),
            username=settings.get("MONGO_APP_USERNAME"),
            password=settings.get("MONGO_APP_PASSWORD"),
            authSource=settings.get("MONGO_APP_DATABASE"),
        )
        repo = LandingMetadataRepository(
            client=mongo_client,
            database=settings.get("MONGO_APP_DATABASE"),
        )
        retry_attempts = settings.getint("LANDING_RETRY_ATTEMPTS", _DEFAULT_RETRY_ATTEMPTS)
        pipeline = cls(object_store=store, metadata_repo=repo, retry_attempts=retry_attempts)
        pipeline._crawler = crawler
        return pipeline

    def close_spider(self, spider: Spider):
        # MongoClient is managed externally in tests; only close when created here.
        if hasattr(self._repo, "_col"):
            try:
                self._repo._col.database.client.close()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Scrapy item pipeline entry point
    # ------------------------------------------------------------------

    def process_item(self, item, spider: Spider):
        try:
            return self._process_item(item, spider)
        except DropItem:
            raise
        except Exception as exc:
            self._inc("landing_pipeline/failed")
            identifier = str(item.get("identifier") or "unknown")
            logger.error(
                "landing_pipeline_failed | identifier=%s error=%s",
                identifier,
                exc,
                exc_info=True,
            )
            raise DropItem(f"Failed to persist {identifier}: {exc}") from exc

    # ------------------------------------------------------------------
    # Internal implementation
    # ------------------------------------------------------------------

    def _process_item(self, item, spider: Spider):
        clean_item(item)

        identifier = item.get("identifier")
        if not identifier:
            raise DropItem("Item has no identifier.")

        payload = self._build_payload(item)
        file_hash = sha256_of_bytes(payload)

        # --- MongoDB-first dedup check (cheaper than a MinIO stat_object) ---
        existing = self._repo.get_by_identifier(str(identifier))
        if existing and existing.get("file_hash") == file_hash and existing.get("path_to_file"):
            path_to_file = str(existing["path_to_file"])
            scrape_status = "unchanged"
            self._inc("landing_pipeline/unchanged")
            logger.debug("Unchanged, skipping upload | identifier=%s", identifier)
        else:
            object_key = build_object_key(
                source=str(item.get("source") or "unknown"),
                body=str(item.get("body") or "unknown"),
                partition_date=str(item.get("partition_date") or "unknown"),
                identifier=str(identifier),
                content_type=str(item.get("content_type") or ""),
                file_name=item.get("file_name"),
                document_url=item.get("link_to_doc"),
            )
            self._with_retries(
                "upload",
                self._store.upload,
                key=object_key,
                data=payload,
                content_type=str(item.get("content_type") or "application/octet-stream"),
                file_hash=file_hash,
            )
            path_to_file = object_key
            scrape_status = "stored"
            self._inc("landing_pipeline/stored")
            logger.info(
                "Uploaded | key=%s size=%d hash=%s", object_key, len(payload), file_hash
            )

        doc = {k: v for k, v in dict(item).items() if k not in ("content_bytes", "content_html")}
        doc["path_to_file"] = path_to_file
        doc["file_hash"] = file_hash
        doc["scrape_status"] = scrape_status
        doc["scraped_at"] = datetime.now(timezone.utc).isoformat()

        self._with_retries(
            "upsert_metadata",
            self._repo.upsert,
            identifier=str(identifier),
            document=doc,
        )

        item["path_to_file"] = path_to_file
        item["file_hash"] = file_hash
        item["scrape_status"] = scrape_status
        # Clear raw content from item — it now lives in MinIO only
        item["content_bytes"] = None
        item["content_html"] = None
        return item

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_payload(self, item) -> bytes:
        if item.get("content_bytes"):
            raw = item["content_bytes"]
            return raw if isinstance(raw, bytes) else bytes(raw)
        if item.get("content_html"):
            return str(item["content_html"]).encode("utf-8")
        return str(item.get("link_to_doc") or "").encode("utf-8")

    def _with_retries(self, operation: str, func, **kwargs):
        last_exc: Exception | None = None
        for attempt in range(1, self._retry_attempts + 1):
            try:
                return func(**kwargs)
            except Exception as exc:
                last_exc = exc
                if attempt < self._retry_attempts:
                    self._inc("landing_pipeline/retries")
                    logger.warning(
                        "Retrying %s (attempt %d/%d) | error=%s",
                        operation,
                        attempt,
                        self._retry_attempts,
                        exc,
                    )
        assert last_exc is not None
        raise last_exc

    def _inc(self, key: str) -> None:
        if self._crawler is not None:
            self._crawler.stats.inc_value(key)
