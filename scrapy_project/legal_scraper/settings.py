import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

BOT_NAME = "legal_scraper"

SPIDER_MODULES = ["legal_scraper.spiders"]
NEWSPIDER_MODULE = "legal_scraper.spiders"

ADDONS: dict[str, Any] = {}

EXTENSIONS = {
    "legal_scraper.extensions.stats_exporter.StatsExporterExtension": 100,
}

ROBOTSTXT_OBEY = True

ITEM_PIPELINES = {
    "legal_scraper.pipelines.LandingZonePipeline": 200,
}

LANDING_RETRY_ATTEMPTS = int(os.environ.get("LANDING_RETRY_ATTEMPTS", 3))

def _require_env(name: str) -> str:
    """Read a required environment variable; raise at startup if missing."""
    value = os.environ.get(name)
    if not value:
        raise EnvironmentError(
            f"Required environment variable '{name}' is not set. "
            "Copy .env.example to .env and fill in the values."
        )
    return value


# MongoDB — landing zone
MONGO_HOST = os.environ.get("MONGO_HOST", "localhost")
MONGO_PORT = int(os.environ.get("MONGO_PORT", 27018))
MONGO_APP_DATABASE = os.environ.get("MONGO_APP_DATABASE", "legal_cases")
MONGO_APP_USERNAME = _require_env("MONGO_APP_USERNAME")
MONGO_APP_PASSWORD = _require_env("MONGO_APP_PASSWORD")

# MinIO — landing zone
MINIO_HOST = os.environ.get("MINIO_HOST", "localhost")
MINIO_PORT = int(os.environ.get("MINIO_PORT", 9000))
MINIO_ROOT_USER = _require_env("MINIO_ROOT_USER")
MINIO_ROOT_PASSWORD = _require_env("MINIO_ROOT_PASSWORD")
MINIO_LANDING_BUCKET = os.environ.get("MINIO_LANDING_BUCKET", "landing-zone")
MINIO_PROCESSED_BUCKET = os.environ.get("MINIO_PROCESSED_BUCKET", "processed-zone")

FEED_EXPORT_ENCODING = "utf-8"

# Autothrottle — adapts request rate to server response times instead of using
# a fixed delay, which is both politer and faster than a static DOWNLOAD_DELAY.
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = float(os.environ.get("AUTOTHROTTLE_START_DELAY", 1.0))
AUTOTHROTTLE_MAX_DELAY = float(os.environ.get("AUTOTHROTTLE_MAX_DELAY", 10.0))
AUTOTHROTTLE_TARGET_CONCURRENCY = float(os.environ.get("AUTOTHROTTLE_TARGET_CONCURRENCY", 2.0))
AUTOTHROTTLE_DEBUG = False
