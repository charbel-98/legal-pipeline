# Architecture

This project uses a layered architecture so scraping, storage, transformation, and orchestration can evolve independently. Scrapy is responsible only for crawling and extraction. Persistence concerns are handled through repository and object-storage adapters, while transformation logic is isolated in a separate service that reads from the landing zone and writes to a processed zone.

MongoDB is used for metadata because the source records are naturally document-shaped and may evolve as scraping progresses. MinIO is used as an S3-compatible local object store because it is simple to run in Docker and mirrors cloud object-storage usage patterns. Raw and processed data are stored in separate buckets and collections to preserve traceability and avoid mutating landing-zone data.

Monthly partitioning is the default starting point because it balances request volume, recovery cost, and logging clarity. Retries and rate limiting are handled through Scrapy settings with conservative concurrency, automatic retry behavior for transient failures, and structured JSON logs per body and partition. Deduplication is handled through a stable record key plus file hashes so reruns do not create duplicate records or redownload unchanged content.

If this pipeline needed to support 50+ sources, the next step would be to standardize the source contract further: one shared ingestion framework, one per-source scraper adapter, source-specific parsers, stronger orchestration, and more operational monitoring around scheduling, failures, and backfills.

