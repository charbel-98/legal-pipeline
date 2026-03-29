import typer

from legal_pipeline.application.config.settings import get_settings
from legal_pipeline.application.logging.logger import configure_logging
from legal_pipeline.application.use_cases.run_scrape import run_scrape
from legal_pipeline.application.use_cases.run_transform import run_transform
from legal_pipeline.infrastructure.db.mongo_repository import MongoMetadataRepository
from legal_pipeline.infrastructure.object_store.minio_storage import MinioObjectStorage
from legal_pipeline.infrastructure.orchestration.dagster_defs import execute_legal_pipeline_job

app = typer.Typer(help="Legal pipeline CLI")


@app.callback()
def main() -> None:
    settings = get_settings()
    configure_logging(settings)


@app.command()
def scrape(
    start_date: str | None = typer.Option(None, "--start-date"),
    end_date: str | None = typer.Option(None, "--end-date"),
    body: str | None = typer.Option(None, "--body"),
    case_number: str | None = typer.Option(None, "--case-number"),
    decision_number: str | None = typer.Option(None, "--decision-number"),
    legislation: str | None = typer.Option(None, "--legislation"),
    topic: str | None = typer.Option(None, "--topic"),
    keyword: str | None = typer.Option(None, "--keyword"),
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
    start_date: str | None = typer.Option(None, "--start-date"),
    end_date: str | None = typer.Option(None, "--end-date"),
) -> None:
    settings = get_settings()
    run_transform(
        start_date or settings.default_start_date,
        end_date or settings.default_end_date,
        metadata_repository=MongoMetadataRepository(settings),
        object_storage=MinioObjectStorage(settings),
    )


@app.command()
def orchestrate(
    start_date: str | None = typer.Option(None, "--start-date"),
    end_date: str | None = typer.Option(None, "--end-date"),
    body: str | None = typer.Option(None, "--body"),
    case_number: str | None = typer.Option(None, "--case-number"),
    decision_number: str | None = typer.Option(None, "--decision-number"),
    legislation: str | None = typer.Option(None, "--legislation"),
    topic: str | None = typer.Option(None, "--topic"),
    keyword: str | None = typer.Option(None, "--keyword"),
) -> None:
    settings = get_settings()
    result = execute_legal_pipeline_job(
        start_date=start_date or settings.default_start_date,
        end_date=end_date or settings.default_end_date,
        body=body,
        case_number=case_number,
        decision_number=decision_number,
        legislation=legislation,
        topic=topic,
        keyword=keyword,
    )
    if not result.success:
        raise typer.Exit(code=1)
