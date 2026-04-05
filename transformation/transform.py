"""
Transformation script — Landing Zone → Processed Zone.

Reads raw scraped files from MinIO landing bucket and metadata from MongoDB
cases_landing collection, then:
  - HTML files: strips navigation/headers/footers with BeautifulSoup,
    renames to {identifier}.html, uploads to processed bucket
  - PDF/DOC files: passes through unchanged, renames to {identifier}.{ext}

Writes processed files to MinIO processed bucket and upserts transformed
metadata into MongoDB cases_processed collection.

Landing data is never modified or deleted.

Usage:
    python transform.py --start-date 2024-01 --end-date 2024-03
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pymongo
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from minio import Minio
from minio.error import S3Error

# ---------------------------------------------------------------------------
# Logging — JSON structured output
# ---------------------------------------------------------------------------

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(message)s",
)
logger = logging.getLogger(__name__)


def _log(event: str, **kwargs) -> None:
    logger.info(json.dumps({"event": event, **kwargs}))


# ---------------------------------------------------------------------------
# Content type helpers
# ---------------------------------------------------------------------------

_EXT_MAP: dict[str, str] = {
    "application/pdf": "pdf",
    "application/msword": "doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.ms-word.document.macroenabled.12": "docm",
    "text/html": "html",
}


def _ext_for_content_type(content_type: str | None) -> str:
    return _EXT_MAP.get(content_type or "", "bin")


# ---------------------------------------------------------------------------
# HTML transformation
# ---------------------------------------------------------------------------

# Tags to remove entirely (navigation chrome, not case content)
_STRIP_TAGS = ["nav", "header", "footer", "script", "style", "noscript"]

# Ordered list of CSS selectors to find the main case content node
_CONTENT_SELECTORS = [
    "article.case-detail",
    "div.case-content",
    "div#main-content",
    "div.content",
    "main",
]


def _process_html(raw: bytes) -> tuple[bytes, str]:
    """Strip chrome from an HTML file and return (cleaned_bytes, sha256_hash)."""
    soup = BeautifulSoup(raw, "html.parser")

    for tag_name in _STRIP_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    # Extract the main content node if possible
    content_node = None
    for selector in _CONTENT_SELECTORS:
        # BeautifulSoup uses CSS select, not the same syntax as Scrapy
        results = soup.select(selector)
        if results:
            content_node = results[0]
            break

    serialized = str(content_node if content_node else soup.body or soup)
    cleaned = serialized.encode("utf-8")
    file_hash = hashlib.sha256(cleaned).hexdigest()
    return cleaned, file_hash


# ---------------------------------------------------------------------------
# MinIO helpers
# ---------------------------------------------------------------------------


def _download_file(client: Minio, bucket: str, key: str) -> bytes:
    """Download an object from MinIO and return its bytes."""
    try:
        response = client.get_object(bucket, key)
        return response.read()
    except S3Error as exc:
        raise RuntimeError(f"Failed to download s3://{bucket}/{key}: {exc}") from exc
    finally:
        try:
            response.close()  # type: ignore[union-attr]
            response.release_conn()  # type: ignore[union-attr]
        except Exception:
            pass


def _upload_file(
    client: Minio,
    bucket: str,
    key: str,
    data: bytes,
    content_type: str,
    file_hash: str,
) -> None:
    """Upload bytes to MinIO, skipping if the hash is unchanged."""
    try:
        stat = client.stat_object(bucket, key)
        existing_hash = (stat.metadata or {}).get("x-amz-meta-file-hash", "")
        if existing_hash == file_hash:
            _log("file_unchanged", key=key)
            return
    except S3Error:
        pass  # Object does not exist yet

    client.put_object(
        bucket,
        key,
        io.BytesIO(data),
        length=len(data),
        content_type=content_type,
        metadata={"file-hash": file_hash},
    )


# ---------------------------------------------------------------------------
# Core record processing
# ---------------------------------------------------------------------------


def _process_record(
    record: dict,
    minio_client: Minio,
    landing_bucket: str,
    processed_bucket: str,
    processed_col,
) -> None:
    """Transform one landing record and write it to the processed zone."""
    identifier = record.get("identifier", "")
    content_type = record.get("content_type", "")
    path_to_file = record.get("path_to_file", "")
    partition_date = record.get("partition_date", "unknown")

    if not path_to_file:
        _log("record_skipped", identifier=identifier, reason="no path_to_file")
        return

    raw = _download_file(minio_client, landing_bucket, path_to_file)

    ext = _ext_for_content_type(content_type)
    new_key = f"processed/{partition_date}/{identifier}.{ext}"

    if content_type == "text/html":
        processed_bytes, file_hash = _process_html(raw)
    else:
        processed_bytes = raw
        file_hash = hashlib.sha256(raw).hexdigest()

    _upload_file(
        minio_client,
        processed_bucket,
        new_key,
        processed_bytes,
        content_type or "application/octet-stream",
        file_hash,
    )

    # Build the processed metadata document
    processed_doc = {k: v for k, v in record.items() if k != "_id"}
    processed_doc["path_to_file"] = new_key
    processed_doc["file_hash"] = file_hash
    processed_doc["processed_at"] = datetime.now(timezone.utc).isoformat()

    processed_col.update_one(
        {"identifier": identifier},
        {"$set": processed_doc},
        upsert=True,
    )

    _log(
        "record_processed",
        identifier=identifier,
        content_type=content_type,
        key=new_key,
        hash=file_hash,
    )


# ---------------------------------------------------------------------------
# MongoDB helpers
# ---------------------------------------------------------------------------


def _get_landing_records(
    collection,
    start_month: str,
    end_month: str,
) -> list[dict]:
    """Fetch all landing records whose partition_date falls in [start, end]."""
    return list(
        collection.find(
            {"partition_date": {"$gte": start_month, "$lte": end_month}}
        )
    )


# ---------------------------------------------------------------------------
# Config and CLI
# ---------------------------------------------------------------------------


def _load_config() -> dict:
    return {
        "mongo_host": os.environ["MONGO_HOST"],
        "mongo_port": int(os.environ.get("MONGO_PORT", 27018)),
        "mongo_database": os.environ["MONGO_APP_DATABASE"],
        "mongo_username": os.environ["MONGO_APP_USERNAME"],
        "mongo_password": os.environ["MONGO_APP_PASSWORD"],
        "minio_host": os.environ["MINIO_HOST"],
        "minio_port": int(os.environ.get("MINIO_PORT", 9000)),
        "minio_user": os.environ["MINIO_ROOT_USER"],
        "minio_password": os.environ["MINIO_ROOT_PASSWORD"],
        "landing_bucket": os.environ.get("MINIO_LANDING_BUCKET", "landing-zone"),
        "processed_bucket": os.environ.get("MINIO_PROCESSED_BUCKET", "processed-zone"),
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Transform landing zone data into the processed zone."
    )
    parser.add_argument(
        "--start-date",
        required=True,
        metavar="YYYY-MM",
        help="First partition month to process (inclusive), e.g. 2024-01",
    )
    parser.add_argument(
        "--end-date",
        required=True,
        metavar="YYYY-MM",
        help="Last partition month to process (inclusive), e.g. 2024-03",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    # Load .env from the project root (two levels up from this file)
    project_root = Path(__file__).parent.parent
    load_dotenv(project_root / ".env")

    args = _parse_args()
    cfg = _load_config()

    # Connect to MongoDB
    mongo_client = pymongo.MongoClient(
        host=cfg["mongo_host"],
        port=cfg["mongo_port"],
        username=cfg["mongo_username"],
        password=cfg["mongo_password"],
        authSource=cfg["mongo_database"],
    )
    db = mongo_client[cfg["mongo_database"]]
    landing_col = db["cases_landing"]
    processed_col = db["cases_processed"]

    # Connect to MinIO
    minio_endpoint = f"{cfg['minio_host']}:{cfg['minio_port']}"
    minio_client = Minio(
        minio_endpoint,
        access_key=cfg["minio_user"],
        secret_key=cfg["minio_password"],
        secure=False,
    )
    if not minio_client.bucket_exists(cfg["processed_bucket"]):
        minio_client.make_bucket(cfg["processed_bucket"])

    records = _get_landing_records(landing_col, args.start_date, args.end_date)
    _log("transform_started", start=args.start_date, end=args.end_date, count=len(records))

    success_count = 0
    fail_count = 0

    for record in records:
        identifier = record.get("identifier", "<unknown>")
        try:
            _process_record(
                record,
                minio_client,
                cfg["landing_bucket"],
                cfg["processed_bucket"],
                processed_col,
            )
            success_count += 1
        except Exception as exc:
            fail_count += 1
            _log("record_failed", identifier=identifier, error=str(exc))

    _log(
        "transform_complete",
        start=args.start_date,
        end=args.end_date,
        processed=success_count,
        failed=fail_count,
    )

    mongo_client.close()


if __name__ == "__main__":
    main()
