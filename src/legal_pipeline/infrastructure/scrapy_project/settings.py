BOT_NAME = "legal_pipeline"

SPIDER_MODULES = ["legal_pipeline.infrastructure.scrapy_project.spiders"]
NEWSPIDER_MODULE = "legal_pipeline.infrastructure.scrapy_project.spiders"

ROBOTSTXT_OBEY = False

CONCURRENT_REQUESTS = 8
DOWNLOAD_DELAY = 0.25
RETRY_TIMES = 3
DOWNLOAD_TIMEOUT = 30
AUTOTHROTTLE_ENABLED = True

LOG_ENABLED = True
