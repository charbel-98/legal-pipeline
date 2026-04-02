import hashlib
import io
import logging
from datetime import datetime, timezone

import pymongo
from minio import Minio
from minio.error import S3Error
from scrapy import Spider
from scrapy.exceptions import DropItem

logger = logging.getLogger(__name__)


def _compute_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _ext_for_content_type(content_type: str | None) -> str:
    mapping = {
        "application/pdf": "pdf",
        "application/msword": "doc",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
        "application/vnd.ms-word.document.macroenabled.12": "docm",
        "text/html": "html",
    }
    return mapping.get(content_type or "", "bin")


class MinIOLandingPipeline:
    """
    Stores raw scraped content (HTML or binary files) in the MinIO landing bucket.

    - Runs before MongoDB so that path_to_file and file_hash are available
      when the metadata record is written.
    - Idempotent: if the object already exists with the same hash it is not
      re-uploaded. If the content changed the object is overwritten.
    - Object key pattern: landing/{partition_date}/{identifier}.{ext}
    """

    def __init__(self, settings):
        self._endpoint = f"{settings.get('MINIO_HOST')}:{settings.getint('MINIO_PORT')}"
        self._access_key = settings.get("MINIO_ROOT_USER")
        self._secret_key = settings.get("MINIO_ROOT_PASSWORD")
        self._bucket = settings.get("MINIO_LANDING_BUCKET")
        self._client: Minio | None = None

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings)

    def open_spider(self, spider: Spider):
        self._client = Minio(
            self._endpoint,
            access_key=self._access_key,
            secret_key=self._secret_key,
            secure=False,
        )
        if not self._client.bucket_exists(self._bucket):
            self._client.make_bucket(self._bucket)
        logger.info(
            "MinIOLandingPipeline ready | endpoint=%s bucket=%s",
            self._endpoint,
            self._bucket,
        )

    def process_item(self, item, spider: Spider):
        identifier = item.get("identifier")
        if not identifier:
            raise DropItem("Item has no identifier — cannot store file.")

        content_type = item.get("content_type")
        ext = _ext_for_content_type(content_type)
        partition = item.get("partition_date") or "unknown"
        object_key = f"landing/{partition}/{identifier}.{ext}"

        # Resolve raw bytes from whichever field the spider populated
        raw: bytes | None = item.get("content_bytes") or (
            item.get("content_html").encode("utf-8")
            if item.get("content_html")
            else None
        )

        if not raw:
            logger.warning("No content to store for %s — skipping upload.", identifier)
            return item

        file_hash = _compute_hash(raw)

        # Check for existing object — skip upload if hash unchanged
        try:
            stat = self._client.stat_object(self._bucket, object_key)
            existing_hash = (stat.metadata or {}).get("x-amz-meta-file-hash", "")
            if existing_hash == file_hash:
                logger.debug("Unchanged file, skipping upload | key=%s", object_key)
                item["path_to_file"] = object_key
                item["file_hash"] = file_hash
                return item
        except S3Error:
            pass  # Object does not exist yet

        self._client.put_object(
            self._bucket,
            object_key,
            io.BytesIO(raw),
            length=len(raw),
            content_type=content_type or "application/octet-stream",
            metadata={"file-hash": file_hash},
        )

        logger.info(
            "Uploaded | key=%s size=%d hash=%s", object_key, len(raw), file_hash
        )

        item["path_to_file"] = object_key
        item["file_hash"] = file_hash
        return item


class MongoLandingPipeline:
    """
    Upserts case metadata into the MongoDB landing collection.

    - Runs after MinIOLandingPipeline so path_to_file and file_hash are set.
    - Upserts by identifier — running twice on the same range will update
      the existing record rather than create a duplicate (idempotent).
    - Raw content bytes/html are stripped before storing — they live in MinIO.
    - Landing data is never deleted or moved; transformation writes to a
      separate collection (cases_processed).
    """

    LANDING_COLLECTION = "cases_landing"

    def __init__(self, settings):
        self._host = settings.get("MONGO_HOST")
        self._port = settings.getint("MONGO_PORT")
        self._database = settings.get("MONGO_APP_DATABASE")
        self._username = settings.get("MONGO_APP_USERNAME")
        self._password = settings.get("MONGO_APP_PASSWORD")
        self._client: pymongo.MongoClient | None = None
        self._collection = None

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings)

    def open_spider(self, spider: Spider):
        self._client = pymongo.MongoClient(
            host=self._host,
            port=self._port,
            username=self._username,
            password=self._password,
            authSource=self._database,
        )
        db = self._client[self._database]
        self._collection = db[self.LANDING_COLLECTION]
        logger.info(
            "MongoLandingPipeline ready | %s:%s/%s/%s",
            self._host,
            self._port,
            self._database,
            self.LANDING_COLLECTION,
        )

    def close_spider(self, spider: Spider):
        if self._client:
            self._client.close()

    def process_item(self, item, spider: Spider):
        identifier = item.get("identifier")
        if not identifier:
            raise DropItem("Item has no identifier — cannot store metadata.")

        doc = dict(item)

        # Raw content must not be persisted in MongoDB
        doc.pop("content_bytes", None)
        doc.pop("content_html", None)

        doc["scraped_at"] = datetime.now(timezone.utc).isoformat()

        self._collection.update_one(
            {"identifier": identifier},
            {"$set": doc},
            upsert=True,
        )

        logger.debug("Upserted metadata | identifier=%s", identifier)
        return item
