"""MinIO implementation of ObjectStore."""

from __future__ import annotations

import io

from minio import Minio
from minio.error import S3Error

from app.storage.object_store import ObjectStore


class MinioStore(ObjectStore):
    def __init__(self, endpoint: str, access_key: str, secret_key: str, bucket: str) -> None:
        self._bucket = bucket
        self._client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=False)
        if not self._client.bucket_exists(self._bucket):
            self._client.make_bucket(self._bucket)

    def upload(self, key: str, data: bytes, content_type: str, file_hash: str) -> None:
        self._client.put_object(
            self._bucket,
            key,
            io.BytesIO(data),
            length=len(data),
            content_type=content_type,
            metadata={"file-hash": file_hash},
        )

    def download(self, key: str) -> bytes:
        response = self._client.get_object(self._bucket, key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def exists_with_hash(self, key: str, file_hash: str) -> bool:
        try:
            stat = self._client.stat_object(self._bucket, key)
            existing = (stat.metadata or {}).get("x-amz-meta-file-hash", "")
            return existing == file_hash
        except S3Error:
            return False
