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
from datetime import date, datetime
from typing import Iterator

import scrapy
from scrapy.http import FormRequest, Request, Response

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

_SEARCH_URL = "https://www.workplacerelations.ie/en/search/?advance=true"

# Maps human-readable body name → (form field name, form field value).
# Values confirmed by inspecting the live search form.
_BODIES: dict[str, tuple[str, str]] = {
    "Employment Appeals Tribunal": ("ctl00$ContentPlaceHolder_Main$CB2$CB2_0", "2"),
    "Equality Tribunal": ("ctl00$ContentPlaceHolder_Main$CB2$CB2_1", "1"),
    "Labour Court": ("ctl00$ContentPlaceHolder_Main$CB2$CB2_2", "3"),
    "Workplace Relations Commission": ("ctl00$ContentPlaceHolder_Main$CB2$CB2_3", "15376"),
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
            self._bodies = _BODIES

        logger.info(
            '{"event": "spider_init", "start_date": "%s", "end_date": "%s", "bodies": %s}',
            self._start_date,
            self._end_date,
            list(self._bodies.keys()),
        )

    # ------------------------------------------------------------------
    # Scrapy lifecycle
    # ------------------------------------------------------------------

    def start_requests(self) -> Iterator[Request]:
        """Yield one FormRequest per (body × monthly partition)."""
        for body_name, (field_name, field_value) in self._bodies.items():
            for p_start, p_end in _monthly_partitions(self._start_date, self._end_date):
                partition_date = p_start.strftime("%Y-%m")

                formdata = {
                    "ctl00$ContentPlaceHolder_Main$TextBox1": "",
                    "ctl00$ContentPlaceHolder_Main$TextBox2": p_start.strftime(_DATE_FMT),
                    "ctl00$ContentPlaceHolder_Main$TextBox3": p_end.strftime(_DATE_FMT),
                    field_name: field_value,
                    "ctl00$ContentPlaceHolder_Main$refine_btn": "",
                }

                logger.info(
                    '{"event": "partition_requested", "body": "%s", "partition": "%s"}',
                    body_name,
                    partition_date,
                )

                yield FormRequest(
                    url=_SEARCH_URL,
                    formdata=formdata,
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
                identifier=case.css("h2.title").attrib.get("title", ""),
                title=case.css("h2.title").attrib.get("title", ""),
                description=case.css("p.description::text").get(default=""),
                case_number=case.css("span.refNO::text").get(default=""),
                record_date=case.css("span.date::text").get(default=""),
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
