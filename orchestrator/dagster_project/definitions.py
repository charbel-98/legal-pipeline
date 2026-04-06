"""Top-level Dagster Definitions — the single entry point loaded by workspace.yaml."""

from dagster import Definitions, EnvVar, load_assets_from_modules

from orchestrator.dagster_project.assets import landing_zone as landing_zone_module
from orchestrator.dagster_project.assets import processed_zone as processed_zone_module
from orchestrator.dagster_project.jobs.full_pipeline_job import full_pipeline_job
from orchestrator.dagster_project.jobs.scrape_job import scrape_job
from orchestrator.dagster_project.jobs.transform_job import transform_job
from orchestrator.dagster_project.resources import MinIOResource, MongoResource

all_assets = load_assets_from_modules([landing_zone_module, processed_zone_module])

defs = Definitions(
    assets=all_assets,
    jobs=[scrape_job, transform_job, full_pipeline_job],
    resources={
        "mongo": MongoResource(
            host=EnvVar("MONGO_HOST"),
            port=EnvVar.int("MONGO_PORT"),
            database=EnvVar("MONGO_APP_DATABASE"),
            username=EnvVar("MONGO_APP_USERNAME"),
            password=EnvVar("MONGO_APP_PASSWORD"),
        ),
        "minio": MinIOResource(
            endpoint=EnvVar("MINIO_ENDPOINT"),
            access_key=EnvVar("MINIO_ROOT_USER"),
            secret_key=EnvVar("MINIO_ROOT_PASSWORD"),
            landing_bucket=EnvVar("MINIO_LANDING_BUCKET"),
            processed_bucket=EnvVar("MINIO_PROCESSED_BUCKET"),
        ),
    },
)
