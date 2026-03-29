from io import BytesIO

from minio import Minio

from legal_pipeline.application.config.settings import Settings
from legal_pipeline.domain.storage.object_storage import ObjectStorage


class MinioObjectStorage(ObjectStorage):
    def __init__(self, settings: Settings) -> None:
        self._client = Minio(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )

    def upload_bytes(
        self, bucket_name: str, object_name: str, payload: bytes, content_type: str
    ) -> str:
        self._client.put_object(
            bucket_name=bucket_name,
            object_name=object_name,
            data=BytesIO(payload),
            length=len(payload),
            content_type=content_type,
        )
        return f"{bucket_name}/{object_name}"

    def download_bytes(self, bucket_name: str, object_name: str) -> bytes:
        response = self._client.get_object(bucket_name, object_name)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()
