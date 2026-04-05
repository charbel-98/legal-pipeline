# Scrapy settings for legal_cases_scraper project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html

import os
from typing import Any

BOT_NAME = "legal_cases_scraper"

SPIDER_MODULES = ["legal_cases_scraper.spiders"]
NEWSPIDER_MODULE = "legal_cases_scraper.spiders"

ADDONS: dict[str, Any] = {}


# Crawl responsibly by identifying yourself (and your website) on the user-agent
# USER_AGENT = "legal_cases_scraper (+http://www.yourdomain.com)"

# Obey robots.txt rules
ROBOTSTXT_OBEY = True

# Concurrency and throttling settings
# CONCURRENT_REQUESTS = 16
CONCURRENT_REQUESTS_PER_DOMAIN = 1
DOWNLOAD_DELAY = 1

# Disable cookies (enabled by default)
# COOKIES_ENABLED = False

# Disable Telnet Console (enabled by default)
# TELNETCONSOLE_ENABLED = False

# Override the default request headers:
# DEFAULT_REQUEST_HEADERS = {
#    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
#    "Accept-Language": "en",
# }

# Enable or disable spider middlewares
# See https://docs.scrapy.org/en/latest/topics/spider-middleware.html
# SPIDER_MIDDLEWARES = {
#    "legal_cases_scraper.middlewares.LegalCasesSpiderMiddleware": 543,
# }

# Enable or disable downloader middlewares
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
# DOWNLOADER_MIDDLEWARES = {
#    "legal_cases_scraper.middlewares.LegalCasesDownloaderMiddleware": 543,
# }

# Enable or disable extensions
# See https://docs.scrapy.org/en/latest/topics/extensions.html
# EXTENSIONS = {
#    "scrapy.extensions.telnet.TelnetConsole": None,
# }

# Configure item pipelines
# See https://docs.scrapy.org/en/latest/topics/item-pipeline.html
ITEM_PIPELINES = {
    # MinIO runs first (priority 200) so path_to_file/file_hash are set
    # before the MongoDB pipeline writes the metadata record.
    "legal_cases_scraper.pipelines.MinIOLandingPipeline": 200,
    "legal_cases_scraper.pipelines.MongoLandingPipeline": 300,
}

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

# Enable and configure the AutoThrottle extension (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/autothrottle.html
# AUTOTHROTTLE_ENABLED = True
# The initial download delay
# AUTOTHROTTLE_START_DELAY = 5
# The maximum download delay to be set in case of high latencies
# AUTOTHROTTLE_MAX_DELAY = 60
# The average number of requests Scrapy should be sending in parallel to
# each remote server
# AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
# Enable showing throttling stats for every response received:
# AUTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
# HTTPCACHE_ENABLED = True
# HTTPCACHE_EXPIRATION_SECS = 0
# HTTPCACHE_DIR = "httpcache"
# HTTPCACHE_IGNORE_HTTP_CODES = []
# HTTPCACHE_STORAGE = "scrapy.extensions.httpcache.FilesystemCacheStorage"

# MinIO — processed zone
MINIO_PROCESSED_BUCKET = os.environ.get("MINIO_PROCESSED_BUCKET", "processed-zone")

# Scraping date range — used as fallback when spider args are not provided
SCRAPE_START_DATE = os.environ.get("SCRAPE_START_DATE", "")
SCRAPE_END_DATE = os.environ.get("SCRAPE_END_DATE", "")

# Set settings whose default value is deprecated to a future-proof value
FEED_EXPORT_ENCODING = "utf-8"
