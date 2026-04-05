"""Dagster op: report curated zone stats after transformation."""

from __future__ import annotations

from dagster import OpExecutionContext, op

from app.services.transformation_service import TransformResult
from orchestrator.dagster_project.resources import MongoResource


@op(
    required_resource_keys={"mongo"},
    description="Log curated record counts and surface them as Dagster metadata.",
)
def publish_curated_metadata(
    context: OpExecutionContext,
    transform_result: TransformResult,
) -> dict[str, int]:
    """Query the processed collection and emit run metadata visible in the Dagster UI."""
    mongo: MongoResource = context.resources.mongo
    client = mongo.get_client()

    try:
        db = client[mongo.database]
        total_curated = db["cases_processed"].count_documents({})
        partition_curated = db["cases_processed"].count_documents(
            {
                "partition_date": {
                    "$gte": transform_result.start_month,
                    "$lte": transform_result.end_month,
                }
            }
        )
    finally:
        client.close()

    context.log.info(
        "Curated zone | range=%s→%s partition_count=%d total_count=%d",
        transform_result.start_month,
        transform_result.end_month,
        partition_curated,
        total_curated,
    )

    # Metadata is surfaced in the Dagster UI run detail panel
    context.add_output_metadata(
        {
            "start_month": transform_result.start_month,
            "end_month": transform_result.end_month,
            "records_in_range": partition_curated,
            "total_curated": total_curated,
            "transform_processed": transform_result.processed,
            "transform_failed": transform_result.failed,
        }
    )

    return {
        "records_in_range": partition_curated,
        "total_curated": total_curated,
    }
