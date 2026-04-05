.PHONY: scrape transform dagster-dev test test-unit reset-db bootstrap install

# ── Dependencies ──────────────────────────────────────────────────────────────
install:
	poetry install

# ── Scraping ──────────────────────────────────────────────────────────────────
scrape:
	python scripts/run_scrape.py \
		--start-date "$(START_DATE)" \
		--end-date "$(END_DATE)"

# ── Transformation ────────────────────────────────────────────────────────────
transform:
	python scripts/run_transform.py \
		--start-date "$(START_MONTH)" \
		--end-date "$(END_MONTH)"

# ── Dagster UI ────────────────────────────────────────────────────────────────
dagster-dev:
	dagster dev

# ── Tests ─────────────────────────────────────────────────────────────────────
test:
	poetry run pytest tests/ -m "not integration" -v

test-unit:
	poetry run pytest tests/unit/ -v

test-integration:
	poetry run pytest tests/integration/ -v

# ── Infrastructure ────────────────────────────────────────────────────────────
up:
	docker compose up -d

down:
	docker compose down

reset-db:
	docker compose down -v
	rm -rf mongo_data/* minio_data/*
	docker compose up -d

bootstrap:
	python scripts/bootstrap_dev.py
