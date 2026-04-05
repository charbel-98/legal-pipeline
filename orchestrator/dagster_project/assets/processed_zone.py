"""
Processed zone asset — partitioned by calendar month, depends on landing_zone.

Materializing this asset for a given partition:
  1. Reads raw files from MinIO landing-zone for that month
  2. Cleans HTML (strips nav/header/footer), passes binary files through
  3. Uploads cleaned files to MinIO processed-zone bucket
  4. Upserts transformed metadata into MongoDB cases_processed collection

The asset is downstream of landing_zone — Dagster enforces that the landing
partition is materialised first, and the lineage graph shows the dependency.
"""

from __future__ import annotations

from datetime import datetime

from dagster import (
    AssetExecutionContext,
    AssetIn,
    MaterializeResult,
    MetadataValue,
    asset,
)

from app.services.transformation_service import run_transformation
from orchestrator.dagster_project.assets.landing_zone import monthly_partitions
from orchestrator.dagster_project.resources import MinIOResource, MongoResource


@asset(
    partitions_def=monthly_partitions,
    ins={"landing_zone": AssetIn()},
    required_resource_keys={"mongo", "minio"},
    group_name="transformation",
    description=(
        "Cleaned and transformed case files for one calendar month. "
        "Stored in MinIO processed-zone and MongoDB cases_processed. "
        "Downstream of landing_zone."
    ),
)
def processed_zone(
    context: AssetExecutionContext,
    landing_zone: MaterializeResult,
) -> MaterializeResult:
    """Transform one month of landing zone records into the processed zone."""
    partition_dt = datetime.strptime(context.partition_key, "%Y-%m-%d")
    partition_label = partition_dt.strftime("%Y-%m")

    context.log.info("Materializing processed_zone | partition=%s", partition_label)

    mongo: MongoResource = context.resources.mongo
    minio: MinIOResource = context.resources.minio

    mongo_client = mongo.get_client()
    minio_client = minio.get_client()

    try:
        result = run_transformation(
            start_month=partition_label,
            end_month=partition_label,
            mongo_client=mongo_client,
            mongo_database=mongo.database,
            minio_client=minio_client,
            landing_bucket="landing-zone",
            processed_bucket="processed-zone",
            log=context.log.info,
        )
    finally:
        mongo_client.close()

    if result.failed > 0:
        context.log.warning(
            "processed_zone | partition=%s failed=%d", partition_label, result.failed
        )

    # Surface stats in the asset materialisation detail panel
    return MaterializeResult(
        metadata={
            "partition": partition_label,
            "records_processed": MetadataValue.int(result.processed),
            "records_failed": MetadataValue.int(result.failed),
        }
    )
