# Code Review Report: Legal Document Scraping Pipeline

**Reviewed against:** Kedra SWE Coding Test requirements
**Dimensions:** Requirements Compliance · Performance & Scalability · Maintainability & Code Quality
**Date:** 2026-03-29

---

## Summary

| Severity | Count |
|----------|-------|
| Critical | 0     |
| High     | 5     |
| Medium   | 11    |
| Low      | 6     |
| **Total**| **22**|

**Requirements compliance: 10/13 PASS, 3 PARTIAL, 0 FAIL.**

---

## Critical (0)

No critical findings. The pipeline is fundamentally sound.

---

## High (5)

### [REQ-4 / REQ-7] Field names deviate from spec
**Location:** `src/legal_pipeline/domain/entities/record.py:16,19`

The spec requires fields named `link_to_doc` and `path_to_file`. The codebase uses `document_url` and `storage_path`. Data is captured correctly but names don't match the spec verbatim — a reviewer checking field names against the PDF will notice immediately.

**Fix:** Rename `document_url` → `link_to_doc` and `storage_path` → `path_to_file` in `record.py` and all dependent code, or add the spec names as aliases.

---

### [PERF-1] Transform loop is fully sequential — no batching or parallelism
**Location:** `src/legal_pipeline/application/use_cases/run_transform.py:40-46`

Each record triggers 3 blocking network round-trips (MinIO download → MinIO upload → MongoDB upsert) with no concurrency. At 1000x scale (500K–1M docs) this is the primary bottleneck.

**Fix:** Use `concurrent.futures.ThreadPoolExecutor` to parallelize `transform_record` calls. Batch `upsert_processed_record` calls using `pymongo.bulk_write` with `UpdateOne` in groups of 500–1000.

---

### [PERF-2] MongoDB upserts are one-at-a-time — no bulk_write
**Location:** `src/legal_pipeline/infrastructure/db/mongo_repository.py:44-49`

Both `upsert_landing_record` and `upsert_processed_record` issue individual `update_one` calls. At scale this means hundreds of thousands of individual round-trips.

**Fix:** Add a `bulk_upsert` path using `pymongo.bulk_write` batched in groups of 500–1000.

---

### [PERF-3] `find_landing_records_by_date_range` loads entire result set into memory
**Location:** `src/legal_pipeline/infrastructure/db/mongo_repository.py:54-57`

`list(cursor)` materializes all matching documents into memory at once. A wide date range query could return hundreds of thousands of documents.

**Fix:** Return the cursor directly (or a generator with `cursor.batch_size(500)`) so the transform loop streams records rather than loading them all up front.

---

### [MAINT-1/2] Application layer directly imports infrastructure — clean architecture violation
**Location:** `src/legal_pipeline/application/use_cases/run_scrape.py:10-22`, `run_transform.py:13-19`

The application use-case modules import concrete infrastructure classes (`MongoMetadataRepository`, `MinioObjectStorage`, Scrapy settings). The application layer should depend only on domain abstractions.

**Fix:** Move infrastructure wiring (construction of concrete implementations) to the composition root in the CLI/Dagster layer, not inside use cases.

---

## Medium (11)

### [MAINT-3] `_parse_iso_date` duplicated in two places
**Location:** `src/legal_pipeline/application/use_cases/run_scrape.py:125`, `src/legal_pipeline/infrastructure/scrapy_project/spiders/workplace_relations_spider.py:222`

Identical function duplicated. Also near-duplicated as `_optional_date` / `_parse_optional_date` in `pipelines.py:177` and `run_transform.py:160`.

**Fix:** Consolidate into `application/services/date_utils.py`.

---

### [MAINT-4] Fake test doubles duplicated across test files
**Location:** `tests/test_landing_zone_pipeline.py:147-198`, `tests/test_run_transform.py:140-191`

`FakeMetadataRepository` and `FakeObjectStorage` are independently re-implemented in two test files with slightly different interfaces. A contract change requires updating both.

**Fix:** Extract shared fakes into `tests/conftest.py` or `tests/fakes.py`.

---

### [MAINT-5] Dummy `DocumentRecord` instantiation used to discover field names
**Location:** `src/legal_pipeline/application/use_cases/run_transform.py:138-155`

Creating a throwaway `DocumentRecord` with empty strings just to call `asdict()` and get field names is fragile. If `DocumentRecord` gains required fields this breaks silently.

**Fix:** Use `dataclasses.fields(DocumentRecord)` directly: `{f.name: landing_record.get(f.name) for f in fields(DocumentRecord)}`.

---

### [MAINT-8] Status values are magic strings scattered across the codebase
**Location:** `src/legal_pipeline/domain/entities/record.py:21`, `src/legal_pipeline/infrastructure/scrapy_project/pipelines.py:78,98`, `src/legal_pipeline/application/use_cases/run_transform.py:134`

Values `"pending"`, `"stored"`, `"unchanged"`, `"scraped"`, `"transformed"` are raw strings. A typo silently produces wrong state with no IDE or type-checker warning.

**Fix:** Define a `ScrapeStatus` string enum in the domain layer and use it consistently everywhere.

---

### [MAINT-9] `MongoClient` connection is never closed
**Location:** `src/legal_pipeline/infrastructure/db/mongo_repository.py:13`

`MongoMetadataRepository.__init__` creates a `MongoClient` but the class has no `close()` method or context manager support. Repeated instantiation (tests, Dagster ops) may leak connections.

**Fix:** Implement `__enter__`/`__exit__` or a `close()` method, and ensure callers manage the lifecycle.

---

### [MAINT-10] Artifacts output path is hardcoded
**Location:** `src/legal_pipeline/application/use_cases/run_scrape.py:68`

`"artifacts/scrape"` is a hardcoded relative path. This is environment-dependent and not configurable through `Settings`.

**Fix:** Add an `artifacts_dir` field to `Settings` backed by an env var.

---

### [MAINT-11] No tests for CLI entry points
**Location:** `src/legal_pipeline/interfaces/cli/main.py`

Default-date fallback logic and `orchestrate` exit-code behaviour are untested. Any regression here would be invisible.

**Fix:** Add basic tests using `typer.testing.CliRunner` with monkeypatched use cases.

---

### [MAINT-12] Test reads spider source code as text instead of testing behaviour
**Location:** `tests/test_query_builder.py:32-37`

Asserting on `"dont_filter=True"` by grepping the source file is a brittle code-text check. It passes even if the logic is dead or wrong.

**Fix:** Instantiate the spider and assert on the yielded `Request` objects' `dont_filter` attribute directly.

---

### [PERF-5] New DB/MinIO clients created on every Dagster op execution
**Location:** `src/legal_pipeline/application/use_cases/run_transform.py:30-31`, `src/legal_pipeline/infrastructure/orchestration/dagster_defs.py:40-49`

Each call to `run_transform` constructs a new `MongoClient` and `Minio` client. Clients are never explicitly closed.

**Fix:** Use Dagster resources to construct clients once per job run and share them between ops.

---

### [PERF-6] `ensure_indexes` called on every `MongoMetadataRepository` instantiation
**Location:** `src/legal_pipeline/infrastructure/db/mongo_repository.py:17`

Issues 5 `create_index` round-trips to MongoDB every time a repository is constructed, including in tests.

**Fix:** Move index creation to a one-time migration/setup step, or guard with a class-level `_indexes_ensured` flag so it runs at most once per process.

---

### [REQ-10] Failed download logs are missing the document URL
**Location:** `src/legal_pipeline/infrastructure/scrapy_project/pipelines.py:59`

The spec requires "failed downloads with URLs and error codes." The current log includes `identifier` and `error` but not the URL.

**Fix:** Add `item.get("document_url")` to the failure log entry.

---

## Low (6)

### [MAINT-6] Spider callback methods lack type annotations
**Location:** `src/legal_pipeline/infrastructure/scrapy_project/spiders/workplace_relations_spider.py:49,59,121,149,185`

Public spider callbacks (`submit_search_form`, `parse_search_results`, etc.) have untyped `response`, `plan`, and `partial_item` parameters.

**Fix:** Add annotations: `response: TextResponse`, `plan: SearchPlan`, `partial_item: dict[str, Any]`.

---

### [MAINT-7] `_build_html_item` / `_build_file_item` share ~80% identical logic
**Location:** `src/legal_pipeline/infrastructure/scrapy_project/spiders/workplace_relations_spider.py:152-219`

These two methods share almost identical field assignment, differing only in `content_bytes`/`content_html` and the default content type. Adding a new item field requires updating both.

**Fix:** Extract a `_build_base_item` helper and specialise only the differing fields.

---

### [MAINT-13] Unused `boto3` and `motor` in dependencies
**Location:** `pyproject.toml:16,20`

Both packages are declared as dependencies but are never imported anywhere in the codebase.

**Fix:** Remove unless actively planned for near-term use.

---

### [MAINT-14] `run_transform` uses raw `hashlib.sha256` instead of `hash_service.sha256_bytes`
**Location:** `src/legal_pipeline/application/use_cases/run_transform.py:5`

Inconsistent with the rest of the codebase which correctly uses `hash_service`.

**Fix:** Replace the direct `hashlib` import with `from legal_pipeline.application.services.hash_service import sha256_bytes`.

---

### [MAINT-15] `ROBOTSTXT_OBEY = False` has no justification comment
**Location:** `src/legal_pipeline/infrastructure/scrapy_project/settings.py:6`

Disabling robots.txt compliance is a deliberate choice that should be documented, especially for a legal data pipeline.

**Fix:** Add a comment explaining why (e.g., the site's robots.txt blocks access to public legal decisions that are meant to be publicly accessible).

---

### [PERF-9] `bytes(response.body)` creates a redundant memory copy
**Location:** `src/legal_pipeline/infrastructure/scrapy_project/spiders/workplace_relations_spider.py:203`

`response.body` is already `bytes`. Wrapping it in `bytes()` creates a full copy unnecessarily.

**Fix:** Use `response.body` directly.

---

## Requirements Compliance Summary

| Requirement | Status | Notes |
|---|---|---|
| REQ-1 Scrapy framework | ✅ PASS | |
| REQ-2 All four bodies | ✅ PASS | |
| REQ-3 Date inputs + monthly partitions | ✅ PASS | |
| REQ-4 Metadata field names | ⚠️ PARTIAL | `document_url` / `storage_path` vs spec's `link_to_doc` / `path_to_file` |
| REQ-5 MongoDB storage | ✅ PASS | |
| REQ-6 Object storage (MinIO) | ✅ PASS | |
| REQ-7 path_to_file in metadata | ⚠️ PARTIAL | Same naming issue as REQ-4 |
| REQ-8 file_hash | ✅ PASS | |
| REQ-9 Idempotency | ✅ PASS | |
| REQ-10 Structured JSON logs | ⚠️ PARTIAL | Missing URL in failure log entries |
| INFRA Docker + Dagster + env vars | ✅ PASS | |
| TRANSFORM script | ✅ PASS | |
| ARCHITECTURE.md | ✅ PASS | |

---

## Top 3 Fixes Before Submission

1. **REQ-4/7** — Rename `document_url` → `link_to_doc` and `storage_path` → `path_to_file` in `record.py` and all callers
2. **REQ-10** — Add `document_url` to the failure log in `pipelines.py:59`
3. **MAINT-8** — Replace status magic strings with a `ScrapeStatus` enum (quick win, demonstrates polish)
