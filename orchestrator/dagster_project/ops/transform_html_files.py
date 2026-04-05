"""Dagster op: transform landing zone records into the processed zone."""

from __future__ import annotations

from dagster import Config, OpExecutionContext, op

from app.services.transformation_service import TransformResult, run_transformation
from orchestrator.dagster_project.resources import MinIOResource, MongoResource


class TransformConfig(Config):
    """Runtime configuration for the standalone transform op.

    Used when running transform_job in isolation. In full_pipeline_job, the
    month range is received from the upstream scrape op instead.
    """

    start_month: str = "2024-01"
    """First partition month to process, YYYY-MM format (inclusive)."""

    end_month: str = "2024-01"
    """Last partition month to process, YYYY-MM format (inclusive)."""


@op(
    required_resource_keys={"mongo", "minio"},
    description="Transform HTML/binary files from the landing zone into the processed zone.",
)
def transform_html_files(
    context: OpExecutionContext,
    config: TransformConfig,
) -> TransformResult:
    """Standalone transform op — reads month range from its own Config."""
    return _run_transform(context, config.start_month, config.end_month)


@op(
    required_resource_keys={"mongo", "minio"},
    description="Transform landing zone records (month range received from upstream scrape op).",
)
def transform_html_files_from_scrape(
    context: OpExecutionContext,
    start_month: str,
    end_month: str,
) -> TransformResult:
    """Pipeline-chained transform op — receives month range from run_scrapy_spider."""
    return _run_transform(context, start_month, end_month)


def _run_transform(
    context: OpExecutionContext,
    start_month: str,
    end_month: str,
) -> TransformResult:
    mongo: MongoResource = context.resources.mongo
    minio: MinIOResource = context.resources.minio

    context.log.info("Transform starting | %s → %s", start_month, end_month)

    mongo_client = mongo.get_client()
    minio_client = minio.get_client()

    try:
        result = run_transformation(
            start_month=start_month,
            end_month=end_month,
            mongo_client=mongo_client,
            mongo_database=mongo.database,
            minio_client=minio_client,
            landing_bucket="landing-zone",
            processed_bucket="processed-zone",
            log=context.log.info,
        )
    finally:
        mongo_client.close()

    context.log.info(
        "Transform complete | processed=%d failed=%d",
        result.processed,
        result.failed,
    )

    if result.failed > 0:
        context.log.warning("%d records failed to transform", result.failed)

    return result
