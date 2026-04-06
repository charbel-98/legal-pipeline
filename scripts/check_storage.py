"""Quick sanity check — prints MongoDB and MinIO landing zone contents."""
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
col = db["cases_landing"]

total = col.count_documents({})
print("=== MongoDB cases_landing ===")
print(f"Total documents: {total}")

by_partition = list(col.aggregate([{"$group": {"_id": "$partition_date", "count": {"$sum": 1}}}]))
for p in sorted(by_partition, key=lambda x: x["_id"]):
    print(f"  {p['_id']}: {p['count']} records")

sample = col.find_one()
if sample:
    print("\nSample document:")
    for k, v in sample.items():
        if k != "_id":
            print(f"  {k}: {v}")
client.close()

# --- MinIO ---
print("\n=== MinIO landing-zone ===")
minio = Minio(
    os.getenv("MINIO_ENDPOINT"),
    access_key=os.getenv("MINIO_ROOT_USER"),
    secret_key=os.getenv("MINIO_ROOT_PASSWORD"),
    secure=False,
)
bucket = os.getenv("MINIO_LANDING_BUCKET")
objects = list(minio.list_objects(bucket, recursive=True))
print(f"Total objects: {len(objects)}")

by_prefix = {}
for obj in objects:
    prefix = "/".join(obj.object_name.split("/")[:2])
    by_prefix[prefix] = by_prefix.get(prefix, 0) + 1
for prefix, count in sorted(by_prefix.items()):
    print(f"  {prefix}: {count} files")

if objects:
    sample_obj = objects[0]
    print(f"\nSample object: {sample_obj.object_name} ({sample_obj.size} bytes)")
