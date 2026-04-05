"""
Landing zone asset — partitioned by calendar month.

Materializing this asset for a given partition:
  1. Runs the Scrapy spider for that month
  2. Uploads raw HTML/PDF/DOC files to MinIO landing-zone bucket
  3. Upserts case metadata into MongoDB cases_landing collection

Each partition key is the first day of the month (YYYY-MM-DD).
In the Dagster UI you select which month(s) to scrape and optionally
filter which legal bodies to include.
"""

from __future__ import annotations

import calendar
from datetime import datetime

from dagster import (
    AssetExecutionContext,
    Config,
    MaterializeResult,
    MetadataValue,
    MonthlyPartitionsDefinition,
    asset,
)

from app.services.ingestion_service import run_scrape
from orchestrator.dagster_project.resources import MongoResource

_ALL_BODIES = [
    "Employment Appeals Tribunal",
    "Equality Tribunal",
    "Labour Court",
    "Workplace Relations Commission",
]

monthly_partitions = MonthlyPartitionsDefinition(start_date="2024-01-01")


class LandingZoneConfig(Config):
    """Configure which legal bodies to scrape for this partition.

    Visible in the Dagster UI Launchpad when materializing this asset.
    """

    bodies: list[str] = _ALL_BODIES
    """Legal bodies to include. Defaults to all four."""


@asset(
    partitions_def=monthly_partitions,
    required_resource_keys={"mongo"},
    group_name="ingestion",
    description=(
        "Raw scraped files and metadata for one calendar month. "
        "Stored in MinIO landing-zone and MongoDB cases_landing."
    ),
)
def landing_zone(
    context: AssetExecutionContext,
    config: LandingZoneConfig,
) -> MaterializeResult:
    """Scrape one month of WRC decisions into the landing zone."""
    # Derive DD/MM/YYYY start/end from the partition key (YYYY-MM-DD)
    partition_dt = datetime.strptime(context.partition_key, "%Y-%m-%d")
    last_day = calendar.monthrange(partition_dt.year, partition_dt.month)[1]
    start_date = partition_dt.strftime("%d/%m/%Y")
    end_date = f"{last_day:02d}/{partition_dt.strftime('%m/%Y')}"
    partition_label = partition_dt.strftime("%Y-%m")

    context.log.info(
        "Materializing landing_zone | partition=%s start=%s end=%s bodies=%s",
        partition_label,
        start_date,
        end_date,
        config.bodies,
    )

    rc = run_scrape(
        start_date=start_date,
        end_date=end_date,
        bodies=config.bodies,
        log=context.log.info,
    )

    if rc != 0:
        raise RuntimeError(f"Scrapy spider exited with code {rc}")

    # Query landing record count for this partition to surface in the UI
    mongo: MongoResource = context.resources.mongo
    client = mongo.get_client()
    try:
        count = client[mongo.database]["cases_landing"].count_documents(
            {"partition_date": partition_label}
        )
    finally:
        client.close()

    context.log.info("Landing zone materialised | partition=%s records=%d", partition_label, count)

    return MaterializeResult(
        metadata={
            "partition": partition_label,
            "bodies_scraped": MetadataValue.json(config.bodies),
            "records_landed": MetadataValue.int(count),
            "start_date": MetadataValue.text(start_date),
            "end_date": MetadataValue.text(end_date),
        }
    )
