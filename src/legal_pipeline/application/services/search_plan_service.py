from dataclasses import dataclass
from datetime import date

from legal_pipeline.application.services.partition_service import (
    DatePartition,
    build_monthly_partitions,
)
from legal_pipeline.domain.entities.search_criteria import SearchCriteria

SUPPORTED_BODIES = (
    "Employment Appeals Tribunal",
    "Equality Tribunal",
    "Labour Court",
    "Workplace Relations Commission",
)


@dataclass(frozen=True, slots=True)
class SearchPlan:
    criteria: SearchCriteria
    partition: DatePartition


def build_search_plans(
    start_date: date,
    end_date: date,
    criteria: SearchCriteria,
) -> list[SearchPlan]:
    partitions = build_monthly_partitions(start_date, end_date)
    bodies = [criteria.body] if criteria.body else list(SUPPORTED_BODIES)

    plans: list[SearchPlan] = []
    for partition in partitions:
        for body in bodies:
            plans.append(
                SearchPlan(
                    criteria=SearchCriteria(
                        body=body,
                        case_number=criteria.case_number,
                        decision_number=criteria.decision_number,
                        legislation=criteria.legislation,
                        topic=criteria.topic,
                        keyword=criteria.keyword,
                    ),
                    partition=partition,
                )
            )

    return plans
