from abc import ABC, abstractmethod


class ObjectStorage(ABC):
    @abstractmethod
    def upload_bytes(self, bucket_name: str, object_name: str, payload: bytes, content_type: str) -> str:
        """Upload raw bytes and return the object path."""

    @abstractmethod
    def download_bytes(self, bucket_name: str, object_name: str) -> bytes:
        """Download an object and return its contents."""

