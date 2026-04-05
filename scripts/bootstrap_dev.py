#!/usr/bin/env python
"""Dev bootstrap — verify connectivity and print connection status.

Usage:
    python scripts/bootstrap_dev.py
"""

from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

import pymongo  # noqa: E402
from minio import Minio  # noqa: E402
from minio.error import S3Error  # noqa: E402

from config.settings import settings  # noqa: E402


def check_mongo() -> None:
    client = pymongo.MongoClient(
        host=settings.mongo_host,
        port=settings.mongo_port,
        username=settings.mongo_username,
        password=settings.mongo_password,
        authSource=settings.mongo_database,
        serverSelectionTimeoutMS=3000,
    )
    client.admin.command("ping")
    db = client[settings.mongo_database]
    landing = db["cases_landing"].count_documents({})
    processed = db["cases_processed"].count_documents({})
    print(f"[OK] MongoDB  | landing={landing}  processed={processed}")
    client.close()


def check_minio() -> None:
    client = Minio(
        settings.minio_endpoint,
        access_key=settings.minio_root_user,
        secret_key=settings.minio_root_password,
        secure=False,
    )
    landing_exists = client.bucket_exists(settings.minio_landing_bucket)
    processed_exists = client.bucket_exists(settings.minio_processed_bucket)
    print(
        f"[OK] MinIO    | landing={settings.minio_landing_bucket}({'✓' if landing_exists else '✗'})  "
        f"processed={settings.minio_processed_bucket}({'✓' if processed_exists else '✗'})"
    )


if __name__ == "__main__":
    try:
        check_mongo()
    except Exception as exc:
        print(f"[FAIL] MongoDB: {exc}")

    try:
        check_minio()
    except Exception as exc:
        print(f"[FAIL] MinIO: {exc}")
