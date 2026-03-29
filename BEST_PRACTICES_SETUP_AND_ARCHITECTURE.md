# Best Practices For Setup And Architecture

## 1. Keep The Project Small But Structured

A strong take-home project should feel production-aware without becoming over-engineered.

Recommended top-level structure:

```text
project/
  scrapy_project/
  app/
    config/
    storage/
    repositories/
    services/
    transforms/
    models/
    logging/
  scripts/
  docker/
  tests/
  README.md
  ARCHITECTURE.md
  .env.example
  docker-compose.yml
```

## 2. Separate Responsibilities Clearly

Avoid mixing crawling, persistence, hashing, and transformation logic together.

A clean split is:

- **Spider**: fetch and parse website content
- **Pipelines/services**: store files, calculate hashes, write metadata
- **Repositories**: database access
- **Transformation module**: process landing files into processed files
- **Orchestrator/job layer**: control execution order and parameters

This separation makes the code easier to test and easier to explain.

## 3. Prefer Config Over Hardcoding

Everything important should come from environment variables or a config file:

- Mongo connection string
- database and collection names
- object storage endpoint
- bucket names
- partition size
- retry counts
- concurrency limits
- output paths
- log level

Best practice:

- commit a `.env.example`
- validate config at startup
- fail fast if required values are missing

## 4. Design For Idempotency From Day One

This is one of the most important parts of the assignment.

Good strategy:

- define a stable unique key per source record, usually using source + body + identifier + document URL
- store file hashes
- before writing a record, check whether it already exists
- if the file hash is unchanged, skip re-download
- if the file changed, save the new file and update the record appropriately

The key idea is:

- same input + same website state = same stored result

## 5. Use Partitioning To Control Risk

Monthly partitions are usually a strong default for this kind of test because they:

- reduce request bursts
- make retries smaller and cheaper
- make logging and recovery easier
- fit well with legal-document publication patterns

You can mention that weekly partitions may be better if the site returns too many records per month.

## 6. Treat Raw And Processed Data As Different Zones

Do not overwrite landing data.

Use:

- one bucket or prefix for raw/landing files
- one bucket or prefix for transformed/processed files
- one raw metadata collection
- one processed metadata collection

This preserves traceability and follows common data engineering practice.

## 7. Log In A Structured Way

JSON logs matter here because the assignment asks for them explicitly.

Each important log event should include fields like:

- event
- run_id
- partition_start
- partition_end
- body
- record_identifier
- URL
- status
- error_code
- error_message

At the end of the run, emit a summary with totals.

## 8. Be Careful With Rate Limiting And Retries

Best practice for this test:

- enable retries for temporary failures
- use conservative concurrency first
- use auto-throttling if helpful
- set timeouts
- log repeated failures with enough context

The goal is not maximum aggression. The goal is reliable scraping without being blocked.

## 9. Hash Files Consistently

Use one hash algorithm consistently, such as SHA-256.

Apply it:

- after downloading a raw file
- after transforming an HTML file

Store the hash in metadata so you can:

- detect duplicates
- detect changes between runs
- prove idempotent behavior

## 10. Build For Explainability

Because this is an interview exercise, every choice should be easy to defend.

Good choices are usually:

- common tools over obscure tools
- simple architecture over clever architecture
- explicit naming over compact code
- tested helper functions over giant scripts

## 11. Recommended Architecture Story

If you need to explain the architecture simply:

1. Scrapy ingests website records by body and date partition.
2. Metadata is written to MongoDB and raw files are written to object storage.
3. A transformation job reads raw metadata and files for a date range.
4. HTML content is cleaned, files are renamed by identifier, and outputs are written to a processed zone.
5. Processed metadata is stored separately from landing metadata.

That is a clean and interview-friendly architecture.

## 12. Best Practices During Implementation

- keep functions small and single-purpose
- add type hints
- use dataclasses or typed models for records/config
- write a few focused tests for partitioning, hashing, and dedup logic
- keep README instructions simple and reproducible
- use Docker Compose so the reviewer can run dependencies quickly
- document trade-offs honestly in `ARCHITECTURE.md`

## 13. What Will Make The Submission Feel Strong

- clear folder structure
- reliable local setup
- no hardcoded secrets or paths
- visible idempotency logic
- understandable logs
- a short but thoughtful architecture write-up
- code that feels maintainable, not rushed
