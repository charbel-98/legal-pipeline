"""
Central configuration — reads all environment variables in one place.

Usage:
    from config.settings import settings
    print(settings.mongo_host)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root on import
load_dotenv(Path(__file__).parent.parent / ".env")


@dataclass(frozen=True)
class Settings:
    # MongoDB
    mongo_host: str = field(default_factory=lambda: os.environ.get("MONGO_HOST", "localhost"))
    mongo_port: int = field(default_factory=lambda: int(os.environ.get("MONGO_PORT", 27018)))
    mongo_root_username: str = field(default_factory=lambda: os.environ.get("MONGO_ROOT_USERNAME", "admin"))
    mongo_root_password: str = field(default_factory=lambda: os.environ.get("MONGO_ROOT_PASSWORD", "adminpassword"))
    mongo_database: str = field(default_factory=lambda: os.environ.get("MONGO_APP_DATABASE", "legal_cases"))
    mongo_username: str = field(default_factory=lambda: os.environ.get("MONGO_APP_USERNAME", "scrapy_user"))
    mongo_password: str = field(default_factory=lambda: os.environ.get("MONGO_APP_PASSWORD", "scrapy_password"))

    # MinIO
    minio_host: str = field(default_factory=lambda: os.environ.get("MINIO_HOST", "localhost"))
    minio_port: int = field(default_factory=lambda: int(os.environ.get("MINIO_PORT", 9000)))
    minio_root_user: str = field(default_factory=lambda: os.environ.get("MINIO_ROOT_USER", "minioadmin"))
    minio_root_password: str = field(default_factory=lambda: os.environ.get("MINIO_ROOT_PASSWORD", "minioadmin123"))
    minio_landing_bucket: str = field(default_factory=lambda: os.environ.get("MINIO_LANDING_BUCKET", "landing-zone"))
    minio_processed_bucket: str = field(default_factory=lambda: os.environ.get("MINIO_PROCESSED_BUCKET", "processed-zone"))

    # Scraping
    scrape_start_date: str = field(default_factory=lambda: os.environ.get("SCRAPE_START_DATE", "01/01/2024"))
    scrape_end_date: str = field(default_factory=lambda: os.environ.get("SCRAPE_END_DATE", "31/01/2024"))
    concurrent_requests_per_domain: int = field(default_factory=lambda: int(os.environ.get("CONCURRENT_REQUESTS_PER_DOMAIN", 1)))
    download_delay: int = field(default_factory=lambda: int(os.environ.get("DOWNLOAD_DELAY", 1)))

    @property
    def mongo_uri(self) -> str:
        return (
            f"mongodb://{self.mongo_username}:{self.mongo_password}"
            f"@{self.mongo_host}:{self.mongo_port}/{self.mongo_database}"
            f"?authSource={self.mongo_database}"
        )

    @property
    def minio_endpoint(self) -> str:
        return f"{self.minio_host}:{self.minio_port}"


settings = Settings()
