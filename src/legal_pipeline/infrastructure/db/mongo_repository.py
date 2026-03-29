from typing import Any

from pymongo import ASCENDING, MongoClient

from legal_pipeline.application.config.settings import Settings
from legal_pipeline.application.services.record_serializer import serialize_record
from legal_pipeline.domain.entities.record import DocumentRecord
from legal_pipeline.domain.repositories.metadata_repository import MetadataRepository


class MongoMetadataRepository(MetadataRepository):
    def __init__(self, settings: Settings) -> None:
        self._client = MongoClient(settings.mongodb_uri)
        self._database = self._client[settings.mongodb_database]
        self._landing_collection = self._database[settings.mongodb_landing_collection]
        self._processed_collection = self._database[settings.mongodb_processed_collection]
        self.ensure_indexes()

    def ensure_indexes(self) -> None:
        identity_index = [
            ("source", ASCENDING),
            ("body", ASCENDING),
            ("identifier", ASCENDING),
        ]
        self._landing_collection.create_index(identity_index, unique=True, name="landing_identity")
        self._processed_collection.create_index(
            identity_index, unique=True, name="processed_identity"
        )
        self._landing_collection.create_index(
            [("partition_date", ASCENDING)], name="landing_partition_date"
        )
        self._landing_collection.create_index(
            [("record_date", ASCENDING)], name="landing_record_date"
        )
        self._landing_collection.create_index([("file_hash", ASCENDING)], name="landing_file_hash")

    def upsert_landing_record(self, record: DocumentRecord) -> None:
        self._landing_collection.update_one(
            {"source": record.source, "body": record.body, "identifier": record.identifier},
            {"$set": serialize_record(record)},
            upsert=True,
        )

    def upsert_processed_record(self, record: DocumentRecord) -> None:
        self._processed_collection.update_one(
            {"source": record.source, "body": record.body, "identifier": record.identifier},
            {"$set": serialize_record(record)},
            upsert=True,
        )

    def find_landing_records_by_date_range(
        self, start_date: str, end_date: str
    ) -> list[dict[str, Any]]:
        cursor = self._landing_collection.find(
            {"partition_date": {"$gte": start_date, "$lte": end_date}}
        )
        return list(cursor)

    def get_landing_record(self, source: str, body: str, identifier: str) -> dict[str, Any] | None:
        return self._landing_collection.find_one(
            {"source": source, "body": body, "identifier": identifier}
        )
