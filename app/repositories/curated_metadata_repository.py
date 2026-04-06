"""MongoDB repository for the cases_processed collection."""

from __future__ import annotations

import pymongo

from app.repositories.metadata_repository import MetadataRepository


class CuratedMetadataRepository(MetadataRepository):
    COLLECTION = "cases_processed"

    def __init__(self, client: pymongo.MongoClient, database: str) -> None:
        self._col = client[database][self.COLLECTION]

    def upsert(self, identifier: str, document: dict) -> None:
        self._col.update_one({"identifier": identifier}, {"$set": document}, upsert=True)

    def find_by_partition_range(self, start_month: str, end_month: str) -> list[dict]:
        return list(
            self._col.find({"partition_date": {"$gte": start_month, "$lte": end_month}})
        )

    def get_by_identifier(self, identifier: str) -> dict | None:
        return self._col.find_one({"identifier": identifier}, {"_id": 0})
