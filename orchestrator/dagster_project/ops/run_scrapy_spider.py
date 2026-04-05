"""Dagster op: run the Scrapy spider for a configurable date range and body filter."""

from __future__ import annotations

from pathlib import Path

from dagster import Config, OpExecutionContext, Out, Output, op

from app.services.ingestion_service import run_scrape

_SCRAPY_DIR = Path(__file__).parent.parent.parent.parent / "scrapy_project"

_ALL_BODIES = [
    "Employment Appeals Tribunal",
    "Equality Tribunal",
    "Labour Court",
    "Workplace Relations Commission",
]


class ScrapeConfig(Config):
    """Runtime configuration for the scrape op.

    Exposed in the Dagster UI Launchpad under ops > run_scrapy_spider > config.
    """

    start_date: str = "01/01/2024"
    """Scrape start date in DD/MM/YYYY format."""

    end_date: str = "31/01/2024"
    """Scrape end date in DD/MM/YYYY format."""

    bodies: list[str] = _ALL_BODIES
    """Legal bodies to scrape. Defaults to all four."""


@op(
    out={"start_month": Out(str), "end_month": Out(str)},
    description="Run the Scrapy spider and populate the MinIO landing zone + MongoDB landing collection.",
)
def run_scrapy_spider(context: OpExecutionContext, config: ScrapeConfig):
    """Scrape Workplace Relations Commission decisions for the configured date range.

    Outputs the derived YYYY-MM month range so downstream ops can consume it
    without duplicating the date configuration.
    """
    from datetime import datetime  # noqa: PLC0415

    context.log.info(
        "Scrape config | start=%s end=%s bodies=%s",
        config.start_date,
        config.end_date,
        config.bodies,
    )

    rc = run_scrape(
        start_date=config.start_date,
        end_date=config.end_date,
        bodies=config.bodies,
        scrapy_project_dir=_SCRAPY_DIR,
        log=context.log.info,
    )

    if rc != 0:
        raise RuntimeError(f"Scrapy spider exited with non-zero code: {rc}")

    # Derive YYYY-MM range from the configured dates for downstream ops
    start_month = datetime.strptime(config.start_date, "%d/%m/%Y").strftime("%Y-%m")
    end_month = datetime.strptime(config.end_date, "%d/%m/%Y").strftime("%Y-%m")

    context.log.info("Scrape complete | landing range: %s → %s", start_month, end_month)

    yield Output(start_month, output_name="start_month")
    yield Output(end_month, output_name="end_month")
