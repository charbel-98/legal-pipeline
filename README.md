# Legal Pipeline

Implementation for the Workplace Relations scraping test. This repository is structured for a clean, scalable pipeline with:

- **Scrapy** for ingestion
- **MongoDB** for metadata
- **MinIO** for object storage
- **Dagster** scaffolding for orchestration
- **BeautifulSoup** for HTML transformation

## Project Structure

```text
src/legal_pipeline/
  application/      # use cases, services, shared config and logging
  domain/           # entities and repository/storage contracts
  infrastructure/   # scrapy, db, object storage, transformation, orchestration adapters
  interfaces/       # CLI and orchestrator entrypoints
tests/              # unit/integration tests
scripts/            # helper scripts
docker/             # extra docker-related assets
```

## Prerequisites

- Python 3.11 or 3.12
- Poetry
- Docker and Docker Compose

## Local Setup

1. Copy the environment file:

```bash
cp .env.example .env
```

Update the placeholder credentials in `.env` before starting Docker or running the app.

2. Install dependencies with Poetry:

```bash
poetry install
```

3. Activate the Poetry shell or prefix commands with `poetry run`:

```bash
poetry shell
```

4. Start infrastructure:

```bash
docker compose up -d
```

5. Verify services:

- MongoDB app URI: use the `MONGODB_URI` value from your local `.env`
- MongoDB admin URI: build it from `MONGO_ROOT_USERNAME` / `MONGO_ROOT_PASSWORD` in your local `.env`
- MinIO API: [http://localhost:9000](http://localhost:9000)
- MinIO Console: [http://localhost:9001](http://localhost:9001)

## CLI Entry Points

Show available commands:

```bash
poetry run legal-pipeline --help
```

Available commands:

- `legal-pipeline scrape`
- `legal-pipeline transform`
- `legal-pipeline orchestrate`

Current scrape filters scaffolded in the CLI:

- `--body`
- `--case-number`
- `--decision-number`
- `--legislation`
- `--topic`
- `--keyword`

## What Is Implemented

- clean architecture package layout
- typed application settings
- rich terminal logging for local runs, with JSON mode still available
- MongoDB repository for landing and processed metadata
- MinIO object storage integration for landing and processed files
- Scrapy crawler for the Workplace Relations search flow
- live Workplace Relations result/detail parsing across all four supported bodies
- landing-zone persistence to MongoDB and MinIO for HTML and PDF records
- transformation service that reads landing records, cleans HTML, and writes processed outputs
- Docker Compose infrastructure
- Poetry-based dependency and virtualenv management

## Example Workflow

Run a small scrape:

```bash
poetry run legal-pipeline scrape --start-date 2024-01-01 --end-date 2024-01-31 --body "Labour Court"
```

Run transformation on a scraped range:

```bash
poetry run legal-pipeline transform --start-date 2024-01-01 --end-date 2024-01-31
```

Verify a PDF-backed transform range:

```bash
poetry run legal-pipeline transform --start-date 2013-01-01 --end-date 2013-01-31
```

That January 2013 range contains `Employment Appeals Tribunal` records with both inline HTML and downloadable PDFs, so it is a good end-to-end verification slice for the processed zone.

## Validation So Far

- scrape validated across:
  - `Labour Court`
  - `Workplace Relations Commission`
  - `Equality Tribunal`
  - `Employment Appeals Tribunal`
- landing zone verified for:
  - HTML records
  - PDF records
- transform verified for:
  - live HTML cleaning
  - live PDF passthrough

## Remaining Work

1. verify a live DOC/DOCX example from the source site if one is exposed
2. enrich processed metadata and reporting where useful
3. add stronger failure summaries and retry reporting for transform runs
4. wire Dagster jobs for ingestion then transformation

## Logging

Local runs now default to a colored terminal logger with icons and concise summaries.

- keep `JSON_LOGS=false` for the richer interactive view
- set `JSON_LOGS=true` if you want machine-readable logs again
- tune verbosity with `LOG_LEVEL`, for example `INFO` or `WARNING`
