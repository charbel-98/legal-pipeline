"""
Transformation service — Landing Zone → Processed Zone.

Reads raw scraped files from MinIO landing bucket and metadata from MongoDB
cases_landing collection, then:
  - HTML files: strips navigation/headers/footers with BeautifulSoup,
    renames to {identifier}.html, uploads to processed bucket
  - PDF/DOC files: passes through unchanged, renames to {identifier}.{ext}

Writes processed files to MinIO processed bucket and upserts transformed
metadata into MongoDB cases_processed collection.

Landing data is never modified or deleted.

CLI entry point: scripts/run_transform.py
"""

from __future__ import annotations

import argparse
import hashlib
import io
import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pymongo
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from minio import Minio
from minio.error import S3Error

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

_STRIP_TAGS = ["nav", "header", "footer", "script", "style", "noscript"]

_CONTENT_SELECTORS = [
    "article.case-detail",
    "div.case-content",
    "div#main-content",
    "div.content",
    "main",
]


def _process_html(raw: bytes) -> tuple[bytes, str]:
    """Strip chrome from an HTML file and return (cleaned_bytes, sha256_hash)."""
    soup = BeautifulSoup(raw.decode("utf-8", errors="replace"), "html.parser")

    for tag_name in _STRIP_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    content_node = None
    for selector in _CONTENT_SELECTORS:
        results = soup.select(selector)
        if results:
            content_node = results[0]
            break

    node = content_node if content_node else soup.body or soup
    html_out = (
        '<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>'
        + str(node)
        + "</body></html>"
    )
    cleaned = html_out.encode("utf-8")
    return cleaned, hashlib.sha256(cleaned).hexdigest()


# ---------------------------------------------------------------------------
# MinIO helpers
# ---------------------------------------------------------------------------


def _download_file(client: Minio, bucket: str, key: str) -> bytes:
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
    log: Callable[[str], None],
) -> None:
    try:
        stat = client.stat_object(bucket, key)
        existing_hash = (stat.metadata or {}).get("x-amz-meta-file-hash", "")
        if existing_hash == file_hash:
            log(f"Skipped (unchanged): {key}")
            return
    except S3Error:
        pass

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
    log: Callable[[str], None],
) -> None:
    identifier = record.get("identifier", "")
    content_type = record.get("content_type", "")
    path_to_file = record.get("path_to_file", "")
    partition_date = record.get("partition_date", "unknown")
    body = (record.get("body") or "unknown").replace(" ", "_")

    if not path_to_file:
        log(f"Skipping {identifier}: no path_to_file")
        return

    raw = _download_file(minio_client, landing_bucket, path_to_file)

    ext = _ext_for_content_type(content_type)
    new_key = f"{body}/{partition_date}/{identifier}.{ext}"

    if content_type == "text/html":
        processed_bytes, file_hash = _process_html(raw)
    else:
        processed_bytes = raw
        file_hash = hashlib.sha256(raw).hexdigest()

    _upload_file(minio_client, processed_bucket, new_key, processed_bytes,
                 content_type or "application/octet-stream", file_hash, log)

    processed_doc = {k: v for k, v in record.items() if k != "_id"}
    processed_doc["path_to_file"] = new_key
    processed_doc["file_hash"] = file_hash
    processed_doc["processed_at"] = datetime.now(timezone.utc).isoformat()

    processed_col.update_one({"identifier": identifier}, {"$set": processed_doc}, upsert=True)
    log(f"Processed: {identifier} → {new_key}")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@dataclass
class TransformResult:
    start_month: str
    end_month: str
    processed: int
    failed: int


def run_transformation(
    start_month: str,
    end_month: str,
    mongo_client: pymongo.MongoClient,
    mongo_database: str,
    minio_client: Minio,
    landing_bucket: str,
    processed_bucket: str,
    body: str | None = None,
    log: Callable[[str], None] | None = None,
) -> TransformResult:
    """Transform landing records for a month range into the processed zone.

    This is the primary callable — used by Dagster ops, scripts, and tests.
    All progress is reported through the injected `log` function so callers
    (Dagster, CLI, tests) control where output goes.

    Args:
        start_month: First partition month, YYYY-MM format (inclusive).
        end_month: Last partition month, YYYY-MM format (inclusive).
        mongo_client: Connected pymongo client.
        mongo_database: Database name.
        minio_client: Connected Minio client.
        landing_bucket: Source MinIO bucket.
        processed_bucket: Destination MinIO bucket.
        log: Logging callable. Defaults to print.

    Returns:
        TransformResult with success/failure counts.
    """
    log = log or print

    db = mongo_client[mongo_database]
    landing_col = db["cases_landing"]
    processed_col = db["cases_processed"]

    if not minio_client.bucket_exists(processed_bucket):
        minio_client.make_bucket(processed_bucket)

    query: dict = {"partition_date": {"$gte": start_month, "$lte": end_month}}
    if body:
        query["body"] = body
    records = list(landing_col.find(query))

    log(f"Transform started: {start_month} → {end_month} | {len(records)} records")

    success_count = 0
    fail_count = 0

    for record in records:
        identifier = record.get("identifier", "<unknown>")
        try:
            _process_record(record, minio_client, landing_bucket, processed_bucket, processed_col, log)
            success_count += 1
        except Exception as exc:
            fail_count += 1
            log(f"Failed: {identifier} — {exc}")

    log(f"Transform complete: {success_count} processed, {fail_count} failed")
    return TransformResult(start_month, end_month, success_count, fail_count)


# ---------------------------------------------------------------------------
# CLI entry point (used by scripts/run_transform.py)
# ---------------------------------------------------------------------------


def main() -> None:
    project_root = Path(__file__).parent.parent.parent
    load_dotenv(project_root / ".env")

    parser = argparse.ArgumentParser(description="Transform landing zone → processed zone.")
    parser.add_argument("--start-date", required=True, metavar="YYYY-MM")
    parser.add_argument("--end-date", required=True, metavar="YYYY-MM")
    args = parser.parse_args()

    mongo_client = pymongo.MongoClient(
        host=os.environ["MONGO_HOST"],
        port=int(os.environ.get("MONGO_PORT", 27018)),
        username=os.environ["MONGO_APP_USERNAME"],
        password=os.environ["MONGO_APP_PASSWORD"],
        authSource=os.environ["MONGO_APP_DATABASE"],
    )
    minio_client = Minio(
        f"{os.environ['MINIO_HOST']}:{os.environ.get('MINIO_PORT', 9000)}",
        access_key=os.environ["MINIO_ROOT_USER"],
        secret_key=os.environ["MINIO_ROOT_PASSWORD"],
        secure=False,
    )

    result = run_transformation(
        start_month=args.start_date,
        end_month=args.end_date,
        mongo_client=mongo_client,
        mongo_database=os.environ["MONGO_APP_DATABASE"],
        minio_client=minio_client,
        landing_bucket=os.environ.get("MINIO_LANDING_BUCKET", "landing-zone"),
        processed_bucket=os.environ.get("MINIO_PROCESSED_BUCKET", "processed-zone"),
    )

    mongo_client.close()
    raise SystemExit(0 if result.failed == 0 else 1)


if __name__ == "__main__":
    main()
