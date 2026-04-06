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

from datetime import datetime

from dagster import (
    AssetExecutionContext,
    MaterializeResult,
    MetadataValue,
    MultiPartitionKey,
    asset,
)

from app.services.transformation_service import run_transformation
from orchestrator.dagster_project.assets.landing_zone import landing_zone, landing_zone_partitions
from orchestrator.dagster_project.resources import MinIOResource, MongoResource


@asset(
    partitions_def=landing_zone_partitions,
    deps=[landing_zone],
    required_resource_keys={"mongo", "minio"},
    group_name="transformation",
    description=(
        "Cleaned and transformed case files for one legal body and one calendar month. "
        "Stored in MinIO processed-zone and MongoDB cases_processed. "
        "Downstream of landing_zone."
    ),
)
def processed_zone(
    context: AssetExecutionContext,
) -> MaterializeResult:
    """Transform one body × month of landing zone records into the processed zone."""
    partition_key: MultiPartitionKey = context.partition_key  # type: ignore[assignment]
    body = partition_key.keys_by_dimension["body"]
    month_key = partition_key.keys_by_dimension["month"]

    partition_dt = datetime.strptime(month_key, "%Y-%m-%d")
    partition_label = partition_dt.strftime("%Y-%m")

    context.log.info(
        "Materializing processed_zone | body=%s partition=%s", body, partition_label
    )

    mongo: MongoResource = context.resources.mongo
    minio: MinIOResource = context.resources.minio

    mongo_client = mongo.get_client()
    minio_client = minio.get_client()

    try:
        result = run_transformation(
            start_month=partition_label,
            end_month=partition_label,
            body=body,
            mongo_client=mongo_client,
            mongo_database=mongo.database,
            minio_client=minio_client,
            landing_bucket=minio.landing_bucket,
            processed_bucket=minio.processed_bucket,
            log=context.log.info,
        )
    finally:
        mongo_client.close()

    if result.failed > 0:
        context.log.warning(
            "processed_zone | body=%s partition=%s failed=%d",
            body,
            partition_label,
            result.failed,
        )

    return MaterializeResult(
        metadata={
            "body": MetadataValue.text(body),
            "partition": MetadataValue.text(partition_label),
            "records_processed": MetadataValue.int(result.processed),
            "records_failed": MetadataValue.int(result.failed),
        }
    )
