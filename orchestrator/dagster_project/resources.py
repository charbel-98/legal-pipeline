"""Dagster resources: MongoDB and MinIO connections."""

from __future__ import annotations

import pymongo
from dagster import ConfigurableResource
from minio import Minio


class MongoResource(ConfigurableResource):
    host: str
    port: int = 27018
    database: str
    username: str
    password: str

    def get_client(self) -> pymongo.MongoClient:
        return pymongo.MongoClient(
            host=self.host,
            port=self.port,
            username=self.username,
            password=self.password,
            authSource=self.database,
        )


class MinIOResource(ConfigurableResource):
    endpoint: str
    access_key: str
    secret_key: str
    secure: bool = False
    landing_bucket: str = "landing-zone"
    processed_bucket: str = "processed-zone"

    def get_client(self) -> Minio:
        return Minio(
            self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure,
        )
