from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = Field(default="local", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    json_logs: bool = Field(default=True, alias="JSON_LOGS")

    mongodb_uri: str = Field(alias="MONGODB_URI")
    mongodb_database: str = Field(alias="MONGODB_DATABASE")
    mongodb_landing_collection: str = Field(alias="MONGODB_LANDING_COLLECTION")
    mongodb_processed_collection: str = Field(alias="MONGODB_PROCESSED_COLLECTION")

    minio_endpoint: str = Field(alias="MINIO_ENDPOINT")
    minio_access_key: str = Field(alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(alias="MINIO_SECRET_KEY")
    minio_secure: bool = Field(default=False, alias="MINIO_SECURE")
    minio_landing_bucket: str = Field(alias="MINIO_LANDING_BUCKET")
    minio_processed_bucket: str = Field(alias="MINIO_PROCESSED_BUCKET")

    scrapy_concurrent_requests: int = Field(default=8, alias="SCRAPY_CONCURRENT_REQUESTS")
    scrapy_download_delay: float = Field(default=0.25, alias="SCRAPY_DOWNLOAD_DELAY")
    scrapy_autothrottle_enabled: bool = Field(default=True, alias="SCRAPY_AUTOTHROTTLE_ENABLED")
    scrapy_retry_times: int = Field(default=3, alias="SCRAPY_RETRY_TIMES")
    scrapy_request_timeout: int = Field(default=30, alias="SCRAPY_REQUEST_TIMEOUT")
    scrapy_user_agent: str = Field(default="legal-pipeline-bot/0.1", alias="SCRAPY_USER_AGENT")
    landing_retry_attempts: int = Field(default=3, alias="LANDING_RETRY_ATTEMPTS")

    partition_size: str = Field(default="monthly", alias="PARTITION_SIZE")
    default_start_date: str = Field(alias="DEFAULT_START_DATE")
    default_end_date: str = Field(alias="DEFAULT_END_DATE")

    artifacts_dir: str = Field(default="artifacts/scrape", alias="ARTIFACTS_DIR")

    dagster_home: str = Field(default="/opt/dagster/dagster_home", alias="DAGSTER_HOME")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
