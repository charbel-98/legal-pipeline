"""MinIO download helper for the Scrapy layer."""

from __future__ import annotations

from minio import Minio
from minio.error import S3Error


def download_object(client: Minio, bucket: str, key: str) -> bytes:
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
