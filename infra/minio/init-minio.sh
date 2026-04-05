#!/bin/sh
# Bootstrap MinIO buckets for local development.
# Equivalent to what the minio-init docker-compose service does.
#
# Usage: MINIO_ROOT_USER=minioadmin MINIO_ROOT_PASSWORD=minioadmin123 \
#        MINIO_LANDING_BUCKET=landing-zone MINIO_PROCESSED_BUCKET=processed-zone \
#        ./infra/minio/init-minio.sh

set -e

MINIO_ENDPOINT="${MINIO_HOST:-localhost}:${MINIO_PORT:-9000}"

until mc alias set local "http://${MINIO_ENDPOINT}" "${MINIO_ROOT_USER}" "${MINIO_ROOT_PASSWORD}" 2>/dev/null; do
  echo "Waiting for MinIO..."
  sleep 1
done

mc mb --ignore-existing "local/${MINIO_LANDING_BUCKET}"
mc mb --ignore-existing "local/${MINIO_PROCESSED_BUCKET}"
mc anonymous set private "local/${MINIO_LANDING_BUCKET}"
mc anonymous set private "local/${MINIO_PROCESSED_BUCKET}"

echo "MinIO buckets ready: ${MINIO_LANDING_BUCKET}, ${MINIO_PROCESSED_BUCKET}"
