from dagster import Definitions, job, op


@op
def ingest_op() -> None:
    return None


@op
def transform_op() -> None:
    return None


@job
def legal_pipeline_job() -> None:
    transform_op(ingest_op())


defs = Definitions(jobs=[legal_pipeline_job])

