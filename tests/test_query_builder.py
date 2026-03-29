import asyncio
from datetime import date

from legal_pipeline.application.services.partition_service import DatePartition
from legal_pipeline.application.services.search_plan_service import SearchPlan
from legal_pipeline.domain.entities.search_criteria import SearchCriteria
from legal_pipeline.infrastructure.scrapy_project.query_builder import (
    WorkplaceRelationsQueryBuilder,
)
from legal_pipeline.infrastructure.scrapy_project.spiders.workplace_relations_spider import (
    WorkplaceRelationsSpider,
)


def test_query_builder_creates_results_url_for_body_partition() -> None:
    builder = WorkplaceRelationsQueryBuilder()
    plan = SearchPlan(
        criteria=SearchCriteria(body="Labour Court"),
        partition=DatePartition(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            partition_date="2024-01-01",
        ),
    )

    url = builder.build_results_url(plan, page_number=2)

    assert "decisions=1" in url
    assert "from=01%2F01%2F2024" in url
    assert "to=31%2F01%2F2024" in url
    assert "body=3" in url
    assert "pageNumber=2" in url


def test_spider_start_marks_bootstrap_requests_as_non_filtered() -> None:
    spider = WorkplaceRelationsSpider(start_date="2024-01-01", end_date="2024-01-31")

    async def _collect():
        return [item async for item in spider.start()]

    requests = asyncio.run(_collect())

    assert len(requests) > 0
    assert all(r.dont_filter for r in requests)
