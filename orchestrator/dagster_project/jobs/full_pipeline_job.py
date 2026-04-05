"""Job: materialise the full pipeline (landing → processed) for a partition."""

from dagster import AssetSelection, define_asset_job

from orchestrator.dagster_project.assets.landing_zone import landing_zone
from orchestrator.dagster_project.assets.processed_zone import processed_zone

full_pipeline_job = define_asset_job(
    name="full_pipeline_job",
    selection=AssetSelection.assets(landing_zone, processed_zone),
    description=(
        "End-to-end pipeline: scrape → transform for the selected month partition. "
        "In the Launchpad: choose the partition and optionally filter bodies."
    ),
)
