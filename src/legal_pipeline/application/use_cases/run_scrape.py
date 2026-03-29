from datetime import date
from pathlib import Path

from scrapy.crawler import CrawlerProcess

from legal_pipeline.application.config.settings import get_settings
from legal_pipeline.application.logging.logger import get_logger
from legal_pipeline.application.services.search_plan_service import build_search_plans
from legal_pipeline.domain.entities.search_criteria import SearchCriteria
from legal_pipeline.infrastructure.scrapy_project.settings import (
    AUTOTHROTTLE_ENABLED,
    BOT_NAME,
    CONCURRENT_REQUESTS,
    DOWNLOAD_DELAY,
    DOWNLOAD_TIMEOUT,
    NEWSPIDER_MODULE,
    RETRY_TIMES,
    SPIDER_MODULES,
)
from legal_pipeline.infrastructure.scrapy_project.spiders.workplace_relations_spider import (
    WorkplaceRelationsSpider,
)


def run_scrape(
    start_date: str,
    end_date: str,
    body: str | None = None,
    case_number: str | None = None,
    decision_number: str | None = None,
    legislation: str | None = None,
    topic: str | None = None,
    keyword: str | None = None,
) -> None:
    logger = get_logger(__name__)
    criteria = SearchCriteria(
        body=body,
        case_number=case_number,
        decision_number=decision_number,
        legislation=legislation,
        topic=topic,
        keyword=keyword,
    )
    plans = build_search_plans(
        start_date=_parse_iso_date(start_date),
        end_date=_parse_iso_date(end_date),
        criteria=criteria,
    )

    logger.info(
        "scrape_run_started",
        start_date=start_date,
        end_date=end_date,
        filters=criteria.active_filters(),
        partition_count=len({plan.partition.partition_date for plan in plans}),
        search_plan_count=len(plans),
    )

    for plan in plans:
        logger.debug(
            "search_plan_prepared",
            partition_start=plan.partition.start_date.isoformat(),
            partition_end=plan.partition.end_date.isoformat(),
            partition_date=plan.partition.partition_date,
            filters=plan.criteria.active_filters(),
        )

    artifacts_dir = Path("artifacts/scrape")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    settings = get_settings()
    process = CrawlerProcess(
        settings={
            "BOT_NAME": BOT_NAME,
            "SPIDER_MODULES": SPIDER_MODULES,
            "NEWSPIDER_MODULE": NEWSPIDER_MODULE,
            "CONCURRENT_REQUESTS": settings.scrapy_concurrent_requests or CONCURRENT_REQUESTS,
            "DOWNLOAD_DELAY": settings.scrapy_download_delay or DOWNLOAD_DELAY,
            "RETRY_TIMES": settings.scrapy_retry_times or RETRY_TIMES,
            "DOWNLOAD_TIMEOUT": settings.scrapy_request_timeout or DOWNLOAD_TIMEOUT,
            "AUTOTHROTTLE_ENABLED": settings.scrapy_autothrottle_enabled or AUTOTHROTTLE_ENABLED,
            "USER_AGENT": settings.scrapy_user_agent,
            "LOG_ENABLED": True,
            "LOG_LEVEL": settings.log_level,
            "ITEM_PIPELINES": {
                "legal_pipeline.infrastructure.scrapy_project.pipelines.LandingZonePipeline": 300,
            },
            "FEEDS": {
                str(artifacts_dir / "latest.jsonl"): {
                    "format": "jsonlines",
                    "overwrite": True,
                }
            },
        },
        install_root_handler=False,
    )
    crawler = process.create_crawler(WorkplaceRelationsSpider)
    process.crawl(
        crawler,
        start_date=start_date,
        end_date=end_date,
        body=body,
        case_number=case_number,
        decision_number=decision_number,
        legislation=legislation,
        topic=topic,
        keyword=keyword,
    )
    process.start()
    stats = crawler.stats.get_stats()
    logger.info(
        "scrape_run_finished",
        start_date=start_date,
        end_date=end_date,
        filters=criteria.active_filters(),
        pages_crawled=stats.get("response_received_count", 0),
        items_scraped=stats.get("item_scraped_count", 0),
        stored_count=stats.get("landing_pipeline/stored", 0),
        unchanged_count=stats.get("landing_pipeline/unchanged", 0),
        failed_count=stats.get("landing_pipeline/failed", 0),
        retry_count=stats.get("landing_pipeline/retries", 0),
    )


def _parse_iso_date(raw: str) -> date:
    return date.fromisoformat(raw)
