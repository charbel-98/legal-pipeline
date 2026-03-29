# Task Explanation

## What This Test Is Asking You To Build

You are being asked to build a small but production-minded data pipeline for legal documents from the **Workplace Relations** website using **Scrapy**.

The pipeline has two main stages:

1. **Ingestion / landing zone**
   - Scrape records from the site.
   - Partition the scrape by date ranges between a provided `start_date` and `end_date`.
   - Extract metadata for each record.
   - Download the related file or page content.
   - Store metadata in a NoSQL database.
   - Store files in object/blob storage.

2. **Transformation / processed zone**
   - Read landing-zone metadata and files for a date range.
   - Leave PDF/DOC files unchanged.
   - Clean HTML files so only the useful document content remains.
   - Recalculate the file hash if the HTML changed.
   - Rename every processed file to `identifier.ext`.
   - Save processed files in a new object storage location.
   - Save transformed metadata in a new NoSQL collection.

## What They Will Evaluate

This is not only a scraping task. It is a **pipeline design** task. They want to see:

- correct use of Scrapy
- good date partitioning
- idempotency and deduplication
- error handling and retry behavior
- structured JSON logging
- clean configuration management
- scalable architecture choices
- ability to explain trade-offs clearly in an interview

## Functional Requirements In Plain English

### Scraping

- Use **Scrapy** as the main scraping framework.
- Scrape all relevant bodies listed on the left side of the site.
- Accept `start_date` and `end_date` as inputs.
- Split the overall date range into smaller partitions, for example monthly.
- For each partition, scrape only that time window and attach a `partition_date`.
- Extract metadata such as:
  - title
  - description
  - identifier
  - decision/publication date
  - source URL
  - document URL
  - partition date
- Download the underlying content:
  - PDF/DOC: store as-is
  - HTML page: fetch the page and store the HTML
- Save the file path and file hash in the metadata record.

### Storage

- Use a **NoSQL database** in Docker.
- Use **object/blob storage** in Docker.
- Keep all paths and credentials configurable.

### Idempotency

- Running the same date range twice should not create duplicates.
- Unchanged files should not be downloaded again.
- Use the file hash plus a stable record identity to detect duplicates or changes.

### Logging

Logs must be structured JSON and include:

- partition currently being processed
- body currently being scraped
- records found
- records successfully scraped
- failures with URL and error code
- end-of-run summary

### Transformation

- Read records by date range from the landing collection.
- Fetch the matching files from object storage.
- For HTML files, keep only meaningful document content.
- Recalculate the transformed file hash.
- Rename files to `identifier.ext`.
- Write output to a separate processed storage location.
- Write output metadata to a separate collection.

## A Good Mental Model For The Project

Think of the assignment as four layers:

1. **Scraper layer**
   - Talks to the website and extracts raw records.

2. **Landing storage layer**
   - Saves raw files and raw metadata safely and repeatably.

3. **Transformation layer**
   - Cleans HTML content and standardizes file naming.

4. **Orchestration layer**
   - Runs ingestion first, then transformation, with dependency handling.

## Suggested Deliverables

At minimum, your final repo should contain:

- scraper code
- transformation script
- Docker setup for DB and object storage
- configuration via `.env` or config file
- JSON logging support
- README with run instructions
- `ARCHITECTURE.md`

## What To Keep In Mind During The Interview

You will likely be asked:

- Why did you choose monthly or weekly partitioning?
- How do you prevent duplicates?
- How do you handle failures without losing progress?
- Why did you choose this DB and storage combination?
- How would this design change for 50+ websites?

The strongest solution is usually not the fanciest one. It is the one that is **clear, configurable, reliable, and easy to explain**.
