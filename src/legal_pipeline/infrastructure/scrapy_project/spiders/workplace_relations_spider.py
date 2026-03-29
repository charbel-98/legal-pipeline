from datetime import date, datetime
from urllib.parse import urljoin

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
            identifier = _clean_text(result.css("span.refNO::text").get()) or title

            if not detail_path:
                continue

            yield Request(
                url=urljoin(response.url, detail_path),
                callback=self.parse_detail_page,
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

    def parse_detail_page(self, response, plan, partial_item):
        content_node = response.css("div.content").get()
        case_number = _extract_case_number(response)
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
        item["content_type"] = "text/html"
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
        yield item


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
