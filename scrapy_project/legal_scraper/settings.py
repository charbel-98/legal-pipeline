import os
from typing import Any

BOT_NAME = "legal_scraper"

SPIDER_MODULES = ["legal_scraper.spiders"]
NEWSPIDER_MODULE = "legal_scraper.spiders"

ADDONS: dict[str, Any] = {}

EXTENSIONS = {
    "legal_scraper.extensions.stats_exporter.StatsExporterExtension": 100,
}

ROBOTSTXT_OBEY = True

CONCURRENT_REQUESTS_PER_DOMAIN = int(os.environ.get("CONCURRENT_REQUESTS_PER_DOMAIN", 1))
DOWNLOAD_DELAY = int(os.environ.get("DOWNLOAD_DELAY", 1))

ITEM_PIPELINES = {
    "legal_scraper.pipelines.LandingZonePipeline": 200,
}

LANDING_RETRY_ATTEMPTS = int(os.environ.get("LANDING_RETRY_ATTEMPTS", 3))

# MongoDB — landing zone
MONGO_HOST = os.environ.get("MONGO_HOST", "localhost")
MONGO_PORT = int(os.environ.get("MONGO_PORT", 27018))
MONGO_APP_DATABASE = os.environ.get("MONGO_APP_DATABASE", "legal_cases")
MONGO_APP_USERNAME = os.environ.get("MONGO_APP_USERNAME", "scrapy_user")
MONGO_APP_PASSWORD = os.environ.get("MONGO_APP_PASSWORD", "scrapy_password")

# MinIO — landing zone
MINIO_HOST = os.environ.get("MINIO_HOST", "localhost")
MINIO_PORT = int(os.environ.get("MINIO_PORT", 9000))
MINIO_ROOT_USER = os.environ.get("MINIO_ROOT_USER", "minioadmin")
MINIO_ROOT_PASSWORD = os.environ.get("MINIO_ROOT_PASSWORD", "minioadmin123")
MINIO_LANDING_BUCKET = os.environ.get("MINIO_LANDING_BUCKET", "landing-zone")
MINIO_PROCESSED_BUCKET = os.environ.get("MINIO_PROCESSED_BUCKET", "processed-zone")

# Scraping date range — used as fallback when spider args are not provided
SCRAPE_START_DATE = os.environ.get("SCRAPE_START_DATE", "")
SCRAPE_END_DATE = os.environ.get("SCRAPE_END_DATE", "")

FEED_EXPORT_ENCODING = "utf-8"
