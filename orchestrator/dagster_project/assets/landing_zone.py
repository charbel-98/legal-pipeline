"""
Landing zone asset — partitioned by (body × calendar month).

Each partition is a combination of one legal body and one calendar month.
In the Dagster UI both dimensions are rendered as dropdowns so you never
have to type body names manually.

Materializing a partition:
  1. Runs the Scrapy spider for that body × month combination
  2. Uploads raw HTML/PDF/DOC files to MinIO landing-zone bucket
  3. Upserts case metadata into MongoDB cases_landing collection
"""

import calendar
from datetime import datetime

from dagster import (
    AssetExecutionContext,
    MaterializeResult,
    MetadataValue,
    MonthlyPartitionsDefinition,
    MultiPartitionsDefinition,
    MultiPartitionKey,
    StaticPartitionsDefinition,
    asset,
)

from app.constants import ALL_BODY_NAMES
from app.services.ingestion_service import run_scrape

landing_zone_partitions = MultiPartitionsDefinition(
    {
        "body": StaticPartitionsDefinition(ALL_BODY_NAMES),
        "month": MonthlyPartitionsDefinition(start_date="2012-01-01"),
    }
)


@asset(
    partitions_def=landing_zone_partitions,
    group_name="ingestion",
    description=(
        "Raw scraped files and metadata for one legal body and one calendar month. "
        "Stored in MinIO landing-zone and MongoDB cases_landing."
    ),
)
def landing_zone(context: AssetExecutionContext) -> MaterializeResult:
    """Scrape one body × month combination into the landing zone."""
    partition_key: MultiPartitionKey = context.partition_key  # type: ignore[assignment]
    body = partition_key.keys_by_dimension["body"]
    month_key = partition_key.keys_by_dimension["month"]  # YYYY-MM-DD (first of month)

    partition_dt = datetime.strptime(month_key, "%Y-%m-%d")
    last_day = calendar.monthrange(partition_dt.year, partition_dt.month)[1]
    start_date = partition_dt.strftime("%d/%m/%Y")
    end_date = f"{last_day:02d}/{partition_dt.strftime('%m/%Y')}"
    partition_label = partition_dt.strftime("%Y-%m")

    context.log.info(
        "Materializing landing_zone | body=%s partition=%s start=%s end=%s",
        body,
        partition_label,
        start_date,
        end_date,
    )

    result = run_scrape(
        start_date=start_date,
        end_date=end_date,
        bodies=[body],
        log=context.log.info,
    )

    if not result.success:
        raise RuntimeError(f"Scrapy spider exited with code {result.returncode}")

    context.log.info(
        "Landing zone materialised | body=%s partition=%s stored=%d unchanged=%d failed=%d pages=%d elapsed=%.1fs",
        body,
        partition_label,
        result.stored,
        result.unchanged,
        result.failed,
        result.pages_scraped,
        result.elapsed_seconds,
    )

    return MaterializeResult(
        metadata={
            "body": MetadataValue.text(body),
            "partition": MetadataValue.text(partition_label),
            "start_date": MetadataValue.text(start_date),
            "end_date": MetadataValue.text(end_date),
            "items_stored": MetadataValue.int(result.stored),
            "items_unchanged": MetadataValue.int(result.unchanged),
            "items_failed": MetadataValue.int(result.failed),
            "pages_scraped": MetadataValue.int(result.pages_scraped),
            "elapsed_seconds": MetadataValue.float(result.elapsed_seconds),
        }
    )
