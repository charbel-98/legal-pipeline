# Architecture

## Overview

A two-stage pipeline: **Landing Zone** (raw scrape) → **Processed Zone** (cleaned and renamed). Both stages are Dagster assets backed by MongoDB for metadata and MinIO for file storage.

```
Scrapy spider
    │  FormRequest per (body × month)
    ▼
LandingZonePipeline (Scrapy item pipeline)
    ├─▶ MinIO  landing-zone/{source}/{body}/{YYYY-MM}/{identifier}.{ext}
    └─▶ MongoDB cases_landing

Dagster processed_zone asset (depends on landing_zone)
    ├─▶ MinIO  processed-zone/{body}/{YYYY-MM}/{identifier}.{ext}
    └─▶ MongoDB cases_processed
```

## Partition size: monthly

Monthly partitions balance granularity against overhead. The target website groups records by date and returns up to ~62 000 results; a single yearly range would time out. A daily partition would create excessive Dagster runs (365 × 4 bodies = 1 460 per year). Monthly gives 48 partitions per year — enough to parallelise across bodies while keeping each run small enough to retry cheaply if it fails.

## Anti-blocking strategy

- **ScrapeOps header rotation**: realistic browser User-Agent and Accept headers on every request, loaded at spider open.
- **ScrapeOps proxy** (optional, toggled via `SCRAPEOPS_PROXY_ENABLED`): routes requests through residential proxies when the site rate-limits direct scraping.
- **AUTOTHROTTLE**: adapts request rate dynamically to server response times (target concurrency: 2 req/s). This is politer and faster than a fixed `DOWNLOAD_DELAY`.
- **Retry middleware**: up to 3 retries on 500/502/503/504 with Scrapy's built-in exponential back-off.

## Deduplication strategy

Two layers:
1. **MongoDB upsert on `identifier`** (unique index): running the pipeline twice for the same date range writes exactly one document per case — the second run updates fields in place, it never inserts a duplicate.
2. **File hash skip**: before uploading to MinIO, the pipeline reads the existing object's `x-amz-meta-file-hash` header. If it matches the SHA-256 of the new content the upload is skipped entirely. This prevents re-downloading and re-storing unchanged files even when re-running for the same partition.

## What would change for 50+ sources

| Concern | Current | At 50+ sources |
|---|---|---|
| Spider per source | One spider, one site | One spider class per source; a `SourceRegistry` maps source ID → spider class |
| Partition key | `body × month` | Add `source` as a third partition dimension, or use a separate asset per source |
| Config | Single `.env` | Per-source config stored in MongoDB/Vault; spider factory reads it at runtime |
| Scheduling | Monthly cron | Per-source schedules with different cadences (some sources update daily) |
| Storage | Flat bucket paths | Prefix bucket paths with `{source}/` — already done in landing-zone layout |
| Monitoring | Dagster UI | Add alerting on asset freshness sensors; per-source SLA checks |
| Rate limiting | Single AUTOTHROTTLE | Per-domain `DOWNLOAD_DELAY` overrides; shared proxy pool with per-domain quotas |
