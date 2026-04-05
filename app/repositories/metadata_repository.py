"""Abstract base class for metadata repositories."""

from __future__ import annotations

from abc import ABC, abstractmethod


class MetadataRepository(ABC):
    @abstractmethod
    def upsert(self, identifier: str, document: dict) -> None: ...

    @abstractmethod
    def find_by_partition_range(self, start_month: str, end_month: str) -> list[dict]: ...
