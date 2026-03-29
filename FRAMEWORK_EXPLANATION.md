# Framework Explanation

## Why Scrapy Is The Core Framework

The assignment explicitly requires **Scrapy**, and it is a strong fit because it gives you:

- fast concurrent crawling
- request scheduling and throttling
- retry support
- item pipelines
- per-spider settings
- clean separation between scraping and storage logic

For this test, Scrapy should be the heart of the ingestion stage.

## What Scrapy Should Handle In This Project

Scrapy is best used for:

- building requests for each body and date partition
- parsing search result pages
- extracting metadata records
- following links to HTML detail pages
- sending file download jobs to a storage pipeline
- logging crawl progress

## Main Scrapy Concepts You’ll Probably Use

### Spider

The spider controls:

- accepted input arguments like `start_date` and `end_date`
- generation of date partitions
- iteration over site bodies
- requests to search/listing pages
- parsing of result pages and pagination

### Item

A Scrapy item or dataclass can represent one scraped record with fields such as:

- source
- body
- identifier
- title
- description
- record_date
- partition_date
- document_url
- source_page_url
- storage_path
- file_hash
- content_type
- scrape_status

### Pipelines

Pipelines are a good place for:

- validating required fields
- checking for duplicates
- writing metadata to MongoDB
- downloading and storing files
- computing file hashes
- enriching items with storage metadata

### Settings

Important Scrapy settings for this test may include:

- concurrency
- download delay
- auto-throttle
- retry count
- user agent
- timeout
- JSON logging format

## Recommended Supporting Tools

Scrapy is not enough alone. A practical stack would be:

- **MongoDB** for metadata
- **MinIO** for S3-compatible object storage
- **BeautifulSoup** for HTML transformation
- **Dagster** or **Airflow** for orchestration
- **Docker Compose** for local infrastructure
- **Pydantic** or a config helper for validating environment variables

## A Good Framework Combination For This Test

One clean option is:

- **Scrapy**: scraping and landing-zone ingestion
- **MongoDB**: metadata storage
- **MinIO**: file storage
- **Dagster**: run ingestion, then transformation
- **BeautifulSoup**: HTML cleanup in transformation

Why this is a strong combination:

- all parts are common and interview-friendly
- easy to run locally with Docker
- easy to explain
- supports idempotency and separation of concerns

## How The Framework Pieces Work Together

1. The orchestrator starts the ingestion job.
2. Scrapy receives `start_date` and `end_date`.
3. The spider creates partitions and requests.
4. Pipelines store files in object storage and metadata in MongoDB.
5. The orchestrator starts the transformation job after ingestion finishes.
6. The transformation script reads landing metadata, processes files, and writes processed outputs.

## What Not To Do

- Do not put all logic inside one giant spider file.
- Do not hardcode DB URLs, bucket names, or date windows.
- Do not mix raw and transformed outputs in the same storage path.
- Do not make the spider responsible for every storage detail.
- Do not skip explaining why Scrapy settings were chosen.

## How To Talk About Scrapy In The Interview

A good explanation is:

“Scrapy is the right choice here because it gives controlled concurrency, request retries, structured parsing, and pipeline hooks for storage. I used it for crawling and extraction, while keeping persistence and transformation in separate components so the system stays maintainable.”
