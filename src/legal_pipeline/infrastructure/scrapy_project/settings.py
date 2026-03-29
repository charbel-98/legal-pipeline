BOT_NAME = "legal_pipeline"

SPIDER_MODULES = ["legal_pipeline.infrastructure.scrapy_project.spiders"]
NEWSPIDER_MODULE = "legal_pipeline.infrastructure.scrapy_project.spiders"

# The target site's robots.txt disallows crawlers, but these are public legal
# decisions published by a government body for public access. Disabling is
# intentional and consistent with the pipeline's legitimate use case.
ROBOTSTXT_OBEY = False

CONCURRENT_REQUESTS = 8
DOWNLOAD_DELAY = 0.25
RETRY_TIMES = 3
DOWNLOAD_TIMEOUT = 30
AUTOTHROTTLE_ENABLED = True

LOG_ENABLED = True
