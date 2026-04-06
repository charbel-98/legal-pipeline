"""Wipe all landing and processed zone data from MongoDB and MinIO."""
import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

import pymongo
from minio import Minio

# --- MongoDB ---
client = pymongo.MongoClient(
    host=os.getenv("MONGO_HOST"),
    port=int(os.getenv("MONGO_PORT")),
    username=os.getenv("MONGO_APP_USERNAME"),
    password=os.getenv("MONGO_APP_PASSWORD"),
    authSource=os.getenv("MONGO_APP_DATABASE"),
)
db = client[os.getenv("MONGO_APP_DATABASE")]

result = db["cases_landing"].delete_many({})
print(f"MongoDB: deleted {result.deleted_count} documents from cases_landing")

result = db["cases_processed"].delete_many({})
print(f"MongoDB: deleted {result.deleted_count} documents from cases_processed")

client.close()

# --- MinIO ---
minio = Minio(
    os.getenv("MINIO_ENDPOINT"),
    access_key=os.getenv("MINIO_ROOT_USER"),
    secret_key=os.getenv("MINIO_ROOT_PASSWORD"),
    secure=False,
)

for bucket_env in ("MINIO_LANDING_BUCKET", "MINIO_PROCESSED_BUCKET"):
    bucket = os.getenv(bucket_env)
    if not minio.bucket_exists(bucket):
        print(f"MinIO: bucket {bucket} does not exist, skipping")
        continue
    objects = list(minio.list_objects(bucket, recursive=True))
    for obj in objects:
        minio.remove_object(bucket, obj.object_name)
    print(f"MinIO: deleted {len(objects)} objects from {bucket}")
