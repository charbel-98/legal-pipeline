"""MinIO upload helper for the Scrapy landing pipeline."""

from __future__ import annotations

import io

from minio import Minio
from minio.error import S3Error


def upload_object(
    client: Minio,
    bucket: str,
    key: str,
    data: bytes,
    content_type: str,
    file_hash: str,
) -> bool:
    """Upload data to MinIO. Returns False (skipped) if hash is unchanged.

    Returns:
        True if uploaded, False if skipped (content unchanged).
    """
    try:
        stat = client.stat_object(bucket, key)
        existing_hash = (stat.metadata or {}).get("x-amz-meta-file-hash", "")
        if existing_hash == file_hash:
            return False
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
    return True
