"""Abstract object storage interface."""

from __future__ import annotations

from abc import ABC, abstractmethod


class ObjectStore(ABC):
    @abstractmethod
    def upload(self, key: str, data: bytes, content_type: str, file_hash: str) -> None: ...

    @abstractmethod
    def download(self, key: str) -> bytes: ...

    @abstractmethod
    def exists_with_hash(self, key: str, file_hash: str) -> bool: ...
