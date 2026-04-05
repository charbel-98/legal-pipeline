"""Job: materialise the processed_zone asset only (landing must already exist)."""

from dagster import AssetSelection, define_asset_job

from orchestrator.dagster_project.assets.processed_zone import processed_zone

transform_job = define_asset_job(
    name="transform_job",
    selection=AssetSelection.assets(processed_zone),
    description=(
        "Transform landing zone records for the selected month into the processed zone. "
        "The landing_zone partition for that month must already be materialised."
    ),
)
