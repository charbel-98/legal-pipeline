"""Deduplication helper — checks whether a file has already been stored."""

from __future__ import annotations

from minio import Minio
from minio.error import S3Error


def is_duplicate(client: Minio, bucket: str, key: str, file_hash: str) -> bool:
    """Return True if the object already exists in MinIO with the same hash."""
    try:
        stat = client.stat_object(bucket, key)
        existing_hash = (stat.metadata or {}).get("x-amz-meta-file-hash", "")
        return existing_hash == file_hash
    except S3Error:
        return False
