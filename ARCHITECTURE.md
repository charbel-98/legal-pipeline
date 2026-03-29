# Architecture

This pipeline is split into four layers: ingestion, storage, transformation, and orchestration. Scrapy is responsible for crawling the Workplace Relations site and extracting record-level data. MongoDB stores metadata for both the landing zone and processed zone. MinIO stores the raw and processed document files. The transformation step is intentionally separate from scraping so raw captures are preserved and can be reprocessed without hitting the source site again.

## Why I Chose Monthly Date Partitions

I chose monthly partitions because they are a good balance between site load, operational safety, and simplicity. A full-year scrape in one request is more likely to time out, be rate-limited, or produce large result sets that are harder to retry safely. Daily partitions would reduce risk further, but they would increase request overhead and make normal runs noisier than necessary. Monthly windows are small enough to retry cheaply, large enough to keep the crawl efficient, and map cleanly to the source site's date filters.

## Retries and Rate Limiting

Retries are handled at two layers. At the HTTP layer, Scrapy uses conservative concurrency, download delay, timeout settings, and retry middleware for transient request failures. AutoThrottle is enabled so the crawler can slow down automatically if the target site responds more slowly. At the persistence layer, the landing pipeline retries object-storage uploads before marking an item as failed. This prevents temporary MinIO or network hiccups from causing partial ingestion. Logging is structured so each run can be traced by date range, partition, and body.

## Deduplication Strategy

Deduplication is based on a stable metadata identity plus content hashing. In MongoDB, landing and processed records use a unique key on `source + body + identifier`, which prevents duplicate logical records from being inserted. For reruns, the pipeline computes a SHA-256 hash of the stored content and compares it to the existing record. If the hash is unchanged, the item is marked `unchanged` and is not re-uploaded. This makes the scraper idempotent and allows the same date range to be rerun safely.

## What I Would Change for 50+ Sources

If this needed to support 50+ sources, I would push the current design further toward a source-adapter model. Each source would implement a common ingestion contract for search planning, request building, parsing, and normalization, while sharing the same repository, object-storage, and transformation interfaces. I would also add stronger orchestration for scheduling and backfills, per-source configuration, richer failure metrics, and a clearer schema-normalization layer so downstream processing does not depend on source-specific HTML shapes. In practice, that would turn this from a single-source pipeline into a reusable ingestion platform.
