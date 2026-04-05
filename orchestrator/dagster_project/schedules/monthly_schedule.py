"""Monthly schedule — materialise the full pipeline for the previous calendar month."""

from __future__ import annotations

import calendar
from datetime import date

from dagster import RunRequest, ScheduleEvaluationContext, schedule

from orchestrator.dagster_project.jobs.full_pipeline_job import full_pipeline_job


@schedule(
    job=full_pipeline_job,
    cron_schedule="0 2 1 * *",  # 02:00 UTC on the 1st of every month
    name="monthly_full_pipeline",
    description=(
        "Automatically scrape and transform the previous calendar month "
        "on the 1st of each month."
    ),
)
def monthly_schedule(context: ScheduleEvaluationContext) -> RunRequest:
    """Compute the partition key for the previous calendar month at schedule time."""
    today = (
        context.scheduled_execution_time.date()
        if context.scheduled_execution_time
        else date.today()
    )
    first_of_current = today.replace(day=1)

    if first_of_current.month == 1:
        prev_year, prev_month = first_of_current.year - 1, 12
    else:
        prev_year, prev_month = first_of_current.year, first_of_current.month - 1

    # MonthlyPartitionsDefinition keys are YYYY-MM-DD (first of the month)
    partition_key = f"{prev_year}-{prev_month:02d}-01"

    return RunRequest(
        run_key=partition_key,
        partition_key=partition_key,
    )
