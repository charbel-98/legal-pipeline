from datetime import date, datetime
from urllib.parse import urljoin, urlparse

from scrapy import FormRequest, Request, Spider

from legal_pipeline.application.logging.logger import get_logger
from legal_pipeline.application.services.search_plan_service import build_search_plans
from legal_pipeline.domain.entities.search_criteria import SearchCriteria
from legal_pipeline.infrastructure.scrapy_project.items import WorkplaceRelationsItem
from legal_pipeline.infrastructure.scrapy_project.query_builder import WorkplaceRelationsQueryBuilder


class WorkplaceRelationsSpider(Spider):
    name = "workplace_relations"
    allowed_domains = ["workplacerelations.ie"]

    def __init__(self, start_date: str, end_date: str, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.start_date = start_date
        self.end_date = end_date
        self.query_builder = WorkplaceRelationsQueryBuilder()
        self.app_logger = get_logger(self.name)
        self.criteria = SearchCriteria(
            body=kwargs.get("body"),
            case_number=kwargs.get("case_number"),
            decision_number=kwargs.get("decision_number"),
            legislation=kwargs.get("legislation"),
            topic=kwargs.get("topic"),
            keyword=kwargs.get("keyword"),
        )

    async def start(self):
        for plan in build_search_plans(
            start_date=_parse_iso_date(self.start_date),
            end_date=_parse_iso_date(self.end_date),
            criteria=self.criteria,
        ):
            yield Request(
                url=self.query_builder.base_url + "?advance=true",
                callback=self.submit_search_form,
                cb_kwargs={"plan": plan},
                dont_filter=True,
            )

    def submit_search_form(self, response, plan):
        yield FormRequest.from_response(
            response=response,
            formid="form",
            formdata=self.query_builder.build_formdata(plan),
            clickdata={"id": "refine_btn"},
            callback=self.parse_search_results,
            cb_kwargs={"plan": plan},
        )

    def parse_search_results(self, response, plan):
        total_results = response.css("div.searchhead::text").getall()
        cleaned_total = " ".join(part.strip() for part in total_results if part.strip())
        self.app_logger.info(
            "search_results_loaded",
            partition_date=plan.partition.partition_date,
            filters=plan.criteria.active_filters(),
            url=response.url,
            summary=cleaned_total,
        )

        results = response.css("div.item-list.search-list li.each-item, li.each-item")
        if not results:
            self.app_logger.warning(
                "search_results_empty",
                partition_date=plan.partition.partition_date,
                filters=plan.criteria.active_filters(),
                url=response.url,
            )

        for result in results:
            title = _clean_text(result.css("h2.title a::text").get())
            detail_path = result.css("h2.title a::attr(href)").get()
            description = _clean_text(result.css("p.description::text").getall())
            record_date = _parse_result_date(result.css("span.date::text").get())
            raw_identifier = _clean_text(result.css("span.refNO::text").get())

            if not detail_path:
                continue

            identifier = _resolve_identifier(raw_identifier=raw_identifier, detail_path=detail_path, title=title)

            yield Request(
                url=urljoin(response.url, detail_path),
                callback=self.parse_document_resource,
                cb_kwargs={
                    "plan": plan,
                    "partial_item": {
                        "source": "workplace_relations",
                        "body": plan.criteria.body,
                        "identifier": identifier,
                        "title": title,
                        "description": description,
                        "record_date": record_date.isoformat() if record_date else None,
                        "partition_date": plan.partition.partition_date,
                        "source_page_url": response.url,
                        "document_url": urljoin(response.url, detail_path),
                        "file_name": _file_name_from_url(detail_path),
                    },
                },
            )

        next_page = response.css("ul.pager a.next::attr(href)").get()
        if next_page:
            yield response.follow(
                next_page,
                callback=self.parse_search_results,
                cb_kwargs={"plan": plan},
            )

    def parse_document_resource(self, response, plan, partial_item):
        if _is_download_response(response):
            yield self._build_file_item(response=response, partial_item=partial_item)
            return

        if _has_meaningful_html_content(response):
            yield self._build_html_item(response=response, partial_item=partial_item)
            return

        attachment_href = _extract_attachment_href(response)
        if attachment_href:
            attachment_url = urljoin(response.url, attachment_href)
            yield response.follow(
                attachment_url,
                callback=self.parse_file_download,
                cb_kwargs={
                    "plan": plan,
                    "partial_item": {
                        **partial_item,
                        "document_url": attachment_url,
                        "file_name": _file_name_from_response(response, attachment_url),
                    },
                },
            )
            return

        yield self._build_html_item(response=response, partial_item=partial_item)

    def parse_file_download(self, response, plan, partial_item):
        yield self._build_file_item(response=response, partial_item=partial_item)

    def _build_html_item(self, response, partial_item):
        content_node = response.css("div.content").get()
        case_number = _extract_case_number(response) or partial_item.get("case_number")
        item = WorkplaceRelationsItem()
        item["source"] = partial_item["source"]
        item["body"] = partial_item["body"]
        item["identifier"] = partial_item["identifier"]
        item["title"] = partial_item["title"]
        item["description"] = partial_item["description"]
        item["case_number"] = case_number
        item["record_date"] = partial_item["record_date"]
        item["partition_date"] = partial_item["partition_date"]
        item["source_page_url"] = partial_item["source_page_url"]
        item["document_url"] = partial_item["document_url"]
        item["file_name"] = partial_item.get("file_name") or _file_name_from_response(response, response.url)
        item["content_type"] = _normalize_content_type(response.headers.get("Content-Type")) or "text/html"
        item["content_bytes"] = None
        item["content_html"] = content_node
        item["storage_path"] = None
        item["file_hash"] = None
        item["scrape_status"] = "scraped"

        self.app_logger.info(
            "detail_page_scraped",
            identifier=item["identifier"],
            body=item["body"],
            partition_date=item["partition_date"],
            url=response.url,
        )
        return item

    def _build_file_item(self, response, partial_item):
        item = WorkplaceRelationsItem()
        item["source"] = partial_item["source"]
        item["body"] = partial_item["body"]
        item["identifier"] = partial_item["identifier"]
        item["title"] = partial_item["title"]
        item["description"] = partial_item["description"]
        item["case_number"] = partial_item.get("case_number")
        item["record_date"] = partial_item["record_date"]
        item["partition_date"] = partial_item["partition_date"]
        item["source_page_url"] = partial_item["source_page_url"]
        item["document_url"] = response.url
        item["file_name"] = partial_item.get("file_name") or _file_name_from_response(response, response.url)
        item["content_type"] = _normalize_content_type(response.headers.get("Content-Type")) or "application/octet-stream"
        item["content_bytes"] = bytes(response.body)
        item["content_html"] = None
        item["storage_path"] = None
        item["file_hash"] = None
        item["scrape_status"] = "scraped"

        self.app_logger.info(
            "document_file_downloaded",
            identifier=item["identifier"],
            body=item["body"],
            partition_date=item["partition_date"],
            url=response.url,
            content_type=item["content_type"],
            file_name=item["file_name"],
            size_bytes=len(response.body),
        )
        return item


def _parse_iso_date(raw: str):
    return date.fromisoformat(raw)


def _parse_result_date(raw: str | None) -> date | None:
    if not raw:
        return None
    return datetime.strptime(raw.strip(), "%d/%m/%Y").date()


def _clean_text(raw: str | list[str] | None) -> str | None:
    if raw is None:
        return None
    if isinstance(raw, list):
        raw = " ".join(raw)
    cleaned = " ".join(raw.split())
    return cleaned or None


def _extract_case_number(response) -> str | None:
    candidate = response.css("div.content table b::text").get()
    return _clean_text(candidate)


def _has_meaningful_html_content(response) -> bool:
    content_node = response.css("div.content").get()
    if not content_node:
        return False
    text_content = _clean_text(response.css("div.content ::text").getall())
    return bool(text_content and len(text_content) >= 100)


def _extract_attachment_href(response) -> str | None:
    selectors = [
        "div.content a[href$='.pdf']::attr(href)",
        "div.content a[href$='.doc']::attr(href)",
        "div.content a[href$='.docx']::attr(href)",
    ]
    for selector in selectors:
        href = response.css(selector).get()
        if href:
            return href
    xpath_selectors = [
        "//div[contains(@class, 'content')]//a[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'full case report')]/@href",
        "//div[contains(@class, 'content')]//a[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'view')][contains(@href, '.pdf') or contains(@href, '.doc')]/@href",
    ]
    for selector in xpath_selectors:
        href = response.xpath(selector).get()
        if href:
            return href
    return None


def _is_download_response(response) -> bool:
    content_type = _normalize_content_type(response.headers.get("Content-Type"))
    if content_type in {
        "application/msword",
        "application/pdf",
        "application/vnd.ms-word.document.macroenabled.12",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }:
        return True
    path = urlparse(response.url).path.lower()
    return path.endswith((".pdf", ".doc", ".docx"))


def _normalize_content_type(raw: bytes | str | None) -> str | None:
    if raw is None:
        return None
    if isinstance(raw, bytes):
        raw = raw.decode("latin-1")
    normalized = raw.split(";", 1)[0].strip().lower()
    return normalized or None


def _file_name_from_response(response, fallback_url: str) -> str | None:
    disposition = response.headers.get("Content-Disposition")
    if disposition:
        if isinstance(disposition, bytes):
            disposition = disposition.decode("latin-1")
        for part in disposition.split(";"):
            part = part.strip()
            if part.lower().startswith("filename="):
                return part.split("=", 1)[1].strip().strip("\"")
    return _file_name_from_url(fallback_url)


def _file_name_from_url(url: str | None) -> str | None:
    if not url:
        return None
    name = urlparse(url).path.rsplit("/", 1)[-1]
    return name or None


def _resolve_identifier(raw_identifier: str | None, detail_path: str, title: str | None) -> str | None:
    slug_identifier = _identifier_from_path(detail_path)
    if not raw_identifier:
        return slug_identifier or title
    if raw_identifier.isdigit() and slug_identifier:
        return slug_identifier
    return raw_identifier or slug_identifier or title


def _identifier_from_path(path: str | None) -> str | None:
    file_name = _file_name_from_url(path)
    if not file_name:
        return None
    stem = file_name.rsplit(".", 1)[0]
    cleaned = stem.strip().upper()
    return cleaned or None
