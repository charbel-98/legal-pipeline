"""Wipe only the processed zone (MongoDB cases_processed + MinIO processed-zone)."""
import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

import pymongo
from minio import Minio

client = pymongo.MongoClient(
    host=os.getenv("MONGO_HOST"),
    port=int(os.getenv("MONGO_PORT")),
    username=os.getenv("MONGO_APP_USERNAME"),
    password=os.getenv("MONGO_APP_PASSWORD"),
    authSource=os.getenv("MONGO_APP_DATABASE"),
)
result = client[os.getenv("MONGO_APP_DATABASE")]["cases_processed"].delete_many({})
print(f"MongoDB: deleted {result.deleted_count} documents from cases_processed")
client.close()

minio = Minio(
    os.getenv("MINIO_ENDPOINT"),
    access_key=os.getenv("MINIO_ROOT_USER"),
    secret_key=os.getenv("MINIO_ROOT_PASSWORD"),
    secure=False,
)
bucket = os.getenv("MINIO_PROCESSED_BUCKET")
objects = list(minio.list_objects(bucket, recursive=True))
for obj in objects:
    minio.remove_object(bucket, obj.object_name)
print(f"MinIO: deleted {len(objects)} objects from {bucket}")
