from dagster import Config, Definitions, In, Nothing, OpExecutionContext, job, op
from dagster._core.execution.execute_in_process_result import ExecuteInProcessResult

from legal_pipeline.application.use_cases.run_scrape import run_scrape
from legal_pipeline.application.use_cases.run_transform import run_transform


class LegalPipelineConfig(Config):
    start_date: str
    end_date: str
    body: str | None = None
    case_number: str | None = None
    decision_number: str | None = None
    legislation: str | None = None
    topic: str | None = None
    keyword: str | None = None


@op
def ingest_op(context: OpExecutionContext, config: LegalPipelineConfig) -> Nothing:
    context.log.info(
        "Starting ingestion for %s -> %s",
        config.start_date,
        config.end_date,
    )
    run_scrape(
        start_date=config.start_date,
        end_date=config.end_date,
        body=config.body,
        case_number=config.case_number,
        decision_number=config.decision_number,
        legislation=config.legislation,
        topic=config.topic,
        keyword=config.keyword,
    )
    return None


@op(ins={"upstream": In(Nothing)})
def transform_op(context: OpExecutionContext, config: LegalPipelineConfig) -> None:
    context.log.info(
        "Starting transformation for %s -> %s",
        config.start_date,
        config.end_date,
    )
    run_transform(
        start_date=config.start_date,
        end_date=config.end_date,
    )


@job
def legal_pipeline_job() -> None:
    transform_op(ingest_op())


defs = Definitions(jobs=[legal_pipeline_job])


def build_run_config(
    *,
    start_date: str,
    end_date: str,
    body: str | None = None,
    case_number: str | None = None,
    decision_number: str | None = None,
    legislation: str | None = None,
    topic: str | None = None,
    keyword: str | None = None,
) -> dict[str, dict[str, dict[str, dict[str, str | None]]]]:
    config = {
        "start_date": start_date,
        "end_date": end_date,
        "body": body,
        "case_number": case_number,
        "decision_number": decision_number,
        "legislation": legislation,
        "topic": topic,
        "keyword": keyword,
    }
    return {
        "ops": {
            "ingest_op": {"config": config},
            "transform_op": {"config": config},
        }
    }


def execute_legal_pipeline_job(
    *,
    start_date: str,
    end_date: str,
    body: str | None = None,
    case_number: str | None = None,
    decision_number: str | None = None,
    legislation: str | None = None,
    topic: str | None = None,
    keyword: str | None = None,
) -> ExecuteInProcessResult:
    return legal_pipeline_job.execute_in_process(
        run_config=build_run_config(
            start_date=start_date,
            end_date=end_date,
            body=body,
            case_number=case_number,
            decision_number=decision_number,
            legislation=legislation,
            topic=topic,
            keyword=keyword,
        )
    )
