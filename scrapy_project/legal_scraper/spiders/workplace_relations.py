"""
Spider for scraping legal case decisions from the Workplace Relations Commission.

Responsibilities (Scrapy lifecycle only):
  - Generate one FormRequest per (body × monthly partition)
  - Parse search result pages and follow case detail links
  - Handle pagination
  - Delegate all HTML parsing to legal_scraper.parsers

Usage:
    scrapy crawl workplace_relations \\
        -a start_date=01/01/2024 \\
        -a end_date=31/01/2024
"""

from __future__ import annotations

import calendar
import logging
import os
from datetime import date, datetime
from typing import AsyncIterator, Iterator
import scrapy
from scrapy.http import Request, Response

from legal_scraper.items import LegalCaseItem
from legal_scraper.parsers.document_page_parser import (
    build_item_from_file,
    build_item_from_html,
    extract_attachment_href,
    has_meaningful_html_content,
    is_download_response,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SEARCH_URL = "https://www.workplacerelations.ie/en/search/"

# Maps human-readable body name → body query parameter value.
_BODIES: dict[str, str] = {
    "Employment Appeals Tribunal": "2",
    "Equality Tribunal": "1",
    "Labour Court": "3",
    "Workplace Relations Commission": "15376",
}

_DATE_FMT = "%d/%m/%Y"
_DEFAULT_START = "01/01/2024"
_DEFAULT_END = "31/01/2024"


# ---------------------------------------------------------------------------
# Spider
# ---------------------------------------------------------------------------


class WorkplaceRelationsSpider(scrapy.Spider):
    name = "workplace_relations"
    allowed_domains = ["www.workplacerelations.ie"]

    custom_settings = {
        # Rate limiting for workplacerelations.ie
        "CONCURRENT_REQUESTS_PER_DOMAIN": int(os.environ.get("CONCURRENT_REQUESTS_PER_DOMAIN", 1)),
        "DOWNLOAD_DELAY": int(os.environ.get("DOWNLOAD_DELAY", 1)),
        # Scraping date range — fallback when spider args are not provided
        "SCRAPE_START_DATE": os.environ.get("SCRAPE_START_DATE", ""),
        "SCRAPE_END_DATE": os.environ.get("SCRAPE_END_DATE", ""),
        # ScrapeOps anti-blocking
        "SCRAPEOPS_API_KEY": os.environ.get("SCRAPEOPS_API_KEY", ""),
        "SCRAPEOPS_HEADERS_ENABLED": os.environ.get("SCRAPEOPS_HEADERS_ENABLED", "true").lower() == "true",
        "SCRAPEOPS_PROXY_ENABLED": os.environ.get("SCRAPEOPS_PROXY_ENABLED", "false").lower() == "true",
        "DOWNLOADER_MIDDLEWARES": {
            "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
            "legal_scraper.middlewares.ScrapeOpsHeadersMiddleware": 400,
            "legal_scraper.middlewares.ScrapeOpsProxyMiddleware": 410,
        },
    }

    def __init__(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        bodies: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)

        raw_start = start_date or self.settings.get("SCRAPE_START_DATE") or _DEFAULT_START
        raw_end = end_date or self.settings.get("SCRAPE_END_DATE") or _DEFAULT_END

        self._start_date = _parse_date(raw_start)
        self._end_date = _parse_date(raw_end)

        # bodies is a comma-separated list of body names; defaults to all
        if bodies:
            selected = {b.strip() for b in bodies.split(",")}
            self._bodies = {k: v for k, v in _BODIES.items() if k in selected}
        else:
            self._bodies = dict(_BODIES)

        logger.info(
            '{"event": "spider_init", "start_date": "%s", "end_date": "%s", "bodies": %s}',
            self._start_date,
            self._end_date,
            list(self._bodies.keys()),
        )

    # ------------------------------------------------------------------
    # Scrapy lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> AsyncIterator[Request]:
        """Yield one GET request per (body × monthly partition)."""
        for body_name, body_value in self._bodies.items():
            for p_start, p_end in _monthly_partitions(self._start_date, self._end_date):
                partition_date = p_start.strftime("%Y-%m")

                logger.info(
                    '{"event": "partition_requested", "body": "%s", "partition": "%s"}',
                    body_name,
                    partition_date,
                )

                url = (
                    f"{_SEARCH_URL}?decisions=1"
                    f"&from={p_start.strftime(_DATE_FMT)}"
                    f"&to={p_end.strftime(_DATE_FMT)}"
                    f"&legislationsub=&body={body_value}"
                )

                yield Request(
                    url=url,
                    callback=self.parse_results,
                    meta={
                        "body": body_name,
                        "partition_date": partition_date,
                        "page": 1,
                    },
                )

    def parse_results(self, response: Response) -> Iterator:
        """Parse a search results page and follow each case detail link."""
        body: str = response.meta["body"]
        partition_date: str = response.meta["partition_date"]
        page: int = response.meta.get("page", 1)

        cases = response.css("li.each-item.clearfix")

        logger.info(
            '{"event": "page_scraped", "body": "%s", "partition": "%s", "page": %d, "count": %d}',
            body,
            partition_date,
            page,
            len(cases),
        )

        for case in cases:
            source_page_url = case.css("a.btn.btn-primary::attr(href)").get(
                default=case.css("h2.title a::attr(href)").get(default="")
            )
            if not source_page_url:
                logger.warning(
                    '{"event": "missing_url", "body": "%s", "partition": "%s"}',
                    body,
                    partition_date,
                )
                continue

            partial_item = LegalCaseItem(
                identifier=case.css("span.refNO::text").get(),
                title=case.css("h2.title a::text").get(),
                description=case.css("p.description::text").get(),
                case_number=case.css("span.refNO::text").get(),
                record_date=case.css("span.date::text").get(),
                source="Workplace Relations Commission",
                body=body,
                partition_date=partition_date,
                source_page_url=source_page_url,
            )

            yield response.follow(
                source_page_url,
                callback=self.parse_document_resource,
                meta={"item": partial_item},
            )

        # Follow next page if pagination link is present
        next_href = response.css("a.next::attr(href)").get()
        if next_href:
            yield response.follow(
                next_href,
                callback=self.parse_results,
                meta={**response.meta, "page": page + 1},
            )

    def parse_document_resource(self, response: Response) -> Iterator:
        """Determine content type and build the final item.

        Delegates all parsing to extractors — no parsing logic here.
        """
        item: LegalCaseItem = response.meta["item"]

        if is_download_response(response):
            yield build_item_from_file(response, item)
            return

        if has_meaningful_html_content(response):
            yield build_item_from_html(response, item)
            return

        attachment_href = extract_attachment_href(response)
        if attachment_href:
            yield response.follow(
                attachment_href,
                callback=self.parse_document_resource,
                meta={"item": item},
            )
            return

        # Fallback: treat whatever HTML we received as the case content
        yield build_item_from_html(response, item)


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _parse_date(raw: str) -> date:
    """Parse a DD/MM/YYYY string into a datetime.date."""
    return datetime.strptime(raw.strip(), _DATE_FMT).date()


def _monthly_partitions(start: date, end: date) -> Iterator[tuple[date, date]]:
    """Yield (month_start, month_end) tuples covering [start, end] inclusive."""
    current = start.replace(day=1)
    end_month_start = end.replace(day=1)

    while current <= end_month_start:
        last_day = calendar.monthrange(current.year, current.month)[1]
        month_end = min(current.replace(day=last_day), end)
        yield current, month_end

        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1, day=1)
        else:
            current = current.replace(month=current.month + 1, day=1)
