# Dagster — what you need to know

This project uses Dagster as its orchestrator. If you know Scrapy, think of
Dagster as the thing that decides *when* and *in what order* to run your
spiders, transformation steps, and anything else that touches data — and gives
you a UI to watch it all happen.

---

## Core concepts (mapped to what you already know)

| Dagster term | Plain meaning | Analogy from Scrapy |
|---|---|---|
| **Asset** | A dataset that Dagster manages. Each asset is a Python function that produces something (files, DB records, …) and Dagster tracks whether it is up to date. | A spider that writes items — but Dagster knows *what* was written and *when*. |
| **Partition** | A slice of an asset, usually by time. This project uses monthly partitions: each month is its own independent unit of data. | Running a spider with different `start_date`/`end_date` settings. |
| **Job** | A selection of assets (or ops) packaged together so you can run them in one click. | `scrapy crawl` for a set of spiders. |
| **Schedule** | A cron rule attached to a job. Dagster runs the job automatically on that cadence. | A cron job that calls `scrapy crawl`. |
| **Resource** | A configured connection (database, object store, …) that assets and ops share. | Scrapy `ITEM_PIPELINES` settings wired to a database. |
| **Op** | A lower-level building block. An asset is essentially a named op whose output is tracked. This project uses ops inside jobs for imperative steps that don't produce a dataset on their own. | Individual pipeline methods. |
| **Definitions** | The single object that lists everything Dagster knows about your project (assets, jobs, schedules, resources). Loaded from `workspace.yaml`. | `scrapy.cfg` pointing at your project. |

---

## Project layout

```
orchestrator/
└── dagster_project/
    ├── definitions.py          ← entry point (Definitions object)
    ├── resources.py            ← MongoResource, MinIOResource
    ├── assets/
    │   ├── landing_zone.py     ← Asset 1: scrape → MinIO + MongoDB
    │   └── processed_zone.py   ← Asset 2: clean/transform → MinIO + MongoDB
    ├── jobs/
    │   ├── scrape_job.py       ← runs landing_zone only
    │   ├── transform_job.py    ← runs processed_zone only
    │   └── full_pipeline_job.py← runs landing_zone then processed_zone
    ├── schedules/
    │   └── monthly_schedule.py ← fires full_pipeline_job on the 1st of each month
    └── ops/                    ← lower-level building blocks (used by jobs)
workspace.yaml                  ← tells Dagster where to find definitions.py
dagster.yaml                    ← instance config (SQLite storage path, launchers)
```

---

## The two assets

### `landing_zone` (ingestion group)

- **What it does:** runs the Scrapy spider for a chosen month, uploads raw
  HTML/PDF/DOC files to MinIO `landing-zone` bucket, and upserts metadata
  into MongoDB `cases_landing`.
- **Partition:** one per calendar month (`2024-01-01`, `2024-02-01`, …).
- **Config you can change in the UI:** `bodies` — the list of legal bodies to
  scrape (defaults to all four).

### `processed_zone` (transformation group)

- **What it does:** reads raw files for that month from MinIO, cleans the HTML,
  writes cleaned files to MinIO `processed-zone` bucket, and upserts into
  MongoDB `cases_processed`.
- **Depends on:** `landing_zone` — Dagster will not let you materialise
  `processed_zone` for a partition until `landing_zone` for the same partition
  is green.

---

## How to run it

### 1. Prerequisites

```bash
# copy and fill in credentials
cp .env.example .env

# start MongoDB and MinIO
docker-compose up -d

# install Python dependencies
poetry install
```

### 2. Start the Dagster UI (Dagit)

```bash
# loads workspace.yaml automatically
dagster dev
```

Then open **http://localhost:3000** in your browser.

> `dagster dev` starts both the web server (Dagit) and the daemon (the process
> that fires schedules and sensors) in one command. It is the standard way to
> run Dagster locally.

### 3. Run a pipeline manually from the UI

1. Go to **Assets** in the left sidebar.
2. You will see two asset nodes: `landing_zone` → `processed_zone`.
3. Click **Materialize all** (or click a single asset and choose Materialize).
4. A **Launchpad** dialog appears. Pick the **partition** (month) you want, e.g. `2024-01-01`.
5. Optionally edit the `bodies` config JSON to scrape only some legal bodies.
6. Click **Launch run**. Watch the logs in real time.

### 4. Run a job from the UI

Jobs are pre-packaged asset selections:

| Job | What it runs |
|---|---|
| `scrape_job` | `landing_zone` only |
| `transform_job` | `processed_zone` only |
| `full_pipeline_job` | `landing_zone` then `processed_zone` |

Go to **Jobs** → pick the job → **Launch job** → choose a partition.

### 5. Run from the CLI (no UI)

```bash
# materialize a specific asset for a specific partition
dagster asset materialize \
  --select landing_zone \
  --partition 2024-01-01

# launch a job
dagster job execute \
  -j full_pipeline_job \
  -c '{"ops": {}}' \
  --partition 2024-01-01
```

---

## The monthly schedule

The schedule `monthly_full_pipeline` fires at **02:00 UTC on the 1st of each
month**. It automatically picks the *previous* month as the partition key, so
on 1 Feb it scrapes all of January.

Schedules only run when the **Dagster daemon** is running. `dagster dev` starts
the daemon for you. In production you would run the daemon as a separate
process alongside the web server.

To toggle the schedule on/off: **Automation** → find `monthly_full_pipeline`
→ toggle the switch.

---

## Resources (connections)

Resources are configured via environment variables read from your `.env` file.
You never hardcode credentials in Python — Dagster reads them through
`EnvVar(...)` at startup.

| Resource | Config vars | Used by |
|---|---|---|
| `MongoResource` | `MONGO_HOST`, `MONGO_PORT`, `MONGO_APP_DATABASE`, `MONGO_APP_USERNAME`, `MONGO_APP_PASSWORD` | Both assets |
| `MinIOResource` | `MINIO_ENDPOINT`, `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD` | `processed_zone` |

---

## The asset graph — what Dagster shows you

In the UI under **Assets** you will see a directed graph:

```
landing_zone  →  processed_zone
```

Each node shows:
- **Last materialized** timestamp per partition.
- **Metadata** emitted by the asset (record counts, dates scraped, …).
- **Logs** from the run that produced it.

Click any node → **Show in asset catalog** → **Partitions** tab to see the
status of every month at a glance (green = materialized, grey = never run,
red = failed).

---

## Common commands cheat-sheet

```bash
# start everything locally
dagster dev

# check Dagster can load your definitions without errors
dagster definitions validate

# list all jobs
dagster job list

# list all assets
dagster asset list

# materialize an asset for a partition
dagster asset materialize --select landing_zone --partition 2024-03-01
```

---

## Where Dagster stores its state

`dagster.yaml` points Dagster at a local SQLite database in `.dagster/`.
That directory is git-ignored. It stores run history, logs, and asset
materialization records. Delete it to reset all run history (assets will show
as never materialized again, but your data in MinIO and MongoDB is untouched).
