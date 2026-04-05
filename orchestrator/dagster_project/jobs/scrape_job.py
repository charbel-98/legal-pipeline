"""Job: materialise the landing_zone asset only."""

from dagster import AssetSelection, define_asset_job

from orchestrator.dagster_project.assets.landing_zone import landing_zone

scrape_job = define_asset_job(
    name="scrape_job",
    selection=AssetSelection.assets(landing_zone),
    description=(
        "Scrape WRC decisions for the selected month partition into the landing zone. "
        "In the Launchpad: choose the partition (month) and optionally filter bodies."
    ),
)
