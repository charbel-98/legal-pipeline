from datetime import date

from legal_pipeline.application.services.search_plan_service import (
    SUPPORTED_BODIES,
    build_search_plans,
)
from legal_pipeline.domain.entities.search_criteria import SearchCriteria


def test_build_search_plans_defaults_to_all_bodies() -> None:
    plans = build_search_plans(
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
        criteria=SearchCriteria(),
    )

    assert len(plans) == len(SUPPORTED_BODIES)
    assert {plan.criteria.body for plan in plans} == set(SUPPORTED_BODIES)


def test_build_search_plans_preserves_non_body_filters() -> None:
    plans = build_search_plans(
        start_date=date(2024, 1, 1),
        end_date=date(2024, 2, 29),
        criteria=SearchCriteria(body="Labour Court", topic="Dismissal", keyword="appeal"),
    )

    assert len(plans) == 2
    assert all(plan.criteria.body == "Labour Court" for plan in plans)
    assert all(plan.criteria.topic == "Dismissal" for plan in plans)
    assert all(plan.criteria.keyword == "appeal" for plan in plans)
