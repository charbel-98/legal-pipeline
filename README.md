# Legal Pipeline

A scraping and transformation pipeline for legal case decisions from [workplacerelations.ie](https://www.workplacerelations.ie). Built with Scrapy, Dagster, MongoDB, and MinIO.

## Prerequisites

- Python 3.12+
- [Poetry](https://python-poetry.org/docs/#installation)
- Docker and Docker Compose

## Quick start

```bash
# 1. Clone and enter the project
git clone <repo-url>
cd legal-pipeline

# 2. Configure environment variables
cp .env.example .env
# Edit .env and fill in credentials for MongoDB and MinIO

# 3. Install Python dependencies
make install

# 4. Start MongoDB and MinIO
make up

# 5. Verify connectivity
make bootstrap

# 6. Start the Dagster UI
make dagster-dev
```

Open **http://localhost:3000** in your browser.

## Running the pipeline

All commands are run through `make`. The Makefile sources `.env` automatically so you never need to export variables manually.

### Via the Dagster UI (recommended)

```bash
make dagster-dev
```

1. Go to **Assets** in the sidebar — you will see `landing_zone` → `processed_zone`.
2. Click **Materialize all**, pick a partition (e.g. `2024-01-01`), and click **Launch run**.

### Via the command line

```bash
# Scrape a date range (all 4 legal bodies)
make scrape START_DATE=01/01/2024 END_DATE=31/01/2024

# Scrape a specific body only
make scrape START_DATE=01/01/2024 END_DATE=31/01/2024 BODIES="Labour Court"

# Transform the scraped data
make transform START_MONTH=2024-01 END_MONTH=2024-01
```

Run `make help` to see all available targets.

## Project structure

```
app/                    # Core business logic (services, repositories, storage)
config/                 # Settings loaded from environment variables
scrapy_project/         # Scrapy spider and item pipeline
orchestrator/           # Dagster assets, jobs, schedules, and resources
infra/                  # MongoDB index definitions and MinIO init scripts
scripts/                # CLI entry points for scraping and transformation
tests/                  # Unit and integration tests
```

## Configuration

All settings are read from environment variables. Copy `.env.example` to `.env` and fill in:

| Variable | Description |
|---|---|
| `MONGO_ROOT_USERNAME` | MongoDB root username |
| `MONGO_ROOT_PASSWORD` | MongoDB root password |
| `MONGO_APP_USERNAME` | Application DB username |
| `MONGO_APP_PASSWORD` | Application DB password |
| `MINIO_ROOT_USER` | MinIO access key |
| `MINIO_ROOT_PASSWORD` | MinIO secret key |
| `SCRAPE_START_DATE` | Default scrape start date (DD/MM/YYYY) |
| `SCRAPE_END_DATE` | Default scrape end date (DD/MM/YYYY) |

See `.env.example` for the full list with defaults.

## Running tests

```bash
# Unit tests only (no external services required)
poetry run pytest tests/unit

# All tests (requires running Docker services)
poetry run pytest
```

## Further reading

- [DAGSTER.md](DAGSTER.md) — Dagster concepts, jobs, schedules, and the UI explained
- [ARCHITECTURE.md](ARCHITECTURE.md) — Design decisions, partitioning, and scaling strategy
