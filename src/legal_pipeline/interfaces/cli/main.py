from typing import Optional

import typer

from legal_pipeline.application.config.settings import get_settings
from legal_pipeline.application.logging.logger import configure_logging
from legal_pipeline.application.use_cases.run_scrape import run_scrape
from legal_pipeline.application.use_cases.run_transform import run_transform

app = typer.Typer(help="Legal pipeline CLI")


@app.callback()
def main() -> None:
    settings = get_settings()
    configure_logging(settings)


@app.command()
def scrape(
    start_date: Optional[str] = typer.Option(None, "--start-date"),
    end_date: Optional[str] = typer.Option(None, "--end-date"),
    body: Optional[str] = typer.Option(None, "--body"),
    case_number: Optional[str] = typer.Option(None, "--case-number"),
    decision_number: Optional[str] = typer.Option(None, "--decision-number"),
    legislation: Optional[str] = typer.Option(None, "--legislation"),
    topic: Optional[str] = typer.Option(None, "--topic"),
    keyword: Optional[str] = typer.Option(None, "--keyword"),
) -> None:
    settings = get_settings()
    run_scrape(
        start_date or settings.default_start_date,
        end_date or settings.default_end_date,
        body=body,
        case_number=case_number,
        decision_number=decision_number,
        legislation=legislation,
        topic=topic,
        keyword=keyword,
    )


@app.command()
def transform(
    start_date: Optional[str] = typer.Option(None, "--start-date"),
    end_date: Optional[str] = typer.Option(None, "--end-date"),
) -> None:
    settings = get_settings()
    run_transform(start_date or settings.default_start_date, end_date or settings.default_end_date)
