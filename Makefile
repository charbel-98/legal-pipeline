# Load .env if it exists — exports every variable so child processes inherit them.
# All targets that need credentials (scrapy, python scripts, dagster) use this.
ifneq (,$(wildcard .env))
  include .env
  export
endif

.PHONY: install up down restart logs scrape transform dagster-dev \
        test test-unit test-integration reset-db reset-db-confirm help

# ── Help ──────────────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "Usage: make <target> [VAR=value ...]"
	@echo ""
	@echo "Setup"
	@echo "  install          Install Python dependencies via Poetry"
	@echo "  up               Start MongoDB and MinIO containers"
	@echo "  down             Stop containers"
	@echo "  restart          Stop then start containers"
	@echo "  logs             Tail container logs"
	@echo "  reset-db         Show reset warning"
	@echo "  reset-db-confirm Wipe all data and restart containers (destructive)"
	@echo ""
	@echo "Pipeline"
	@echo "  scrape           Run the Scrapy spider"
	@echo "                   Required: START_DATE=DD/MM/YYYY END_DATE=DD/MM/YYYY"
	@echo "                   Optional: BODIES='Labour Court,Equality Tribunal'"
	@echo "                   Example:  make scrape START_DATE=01/01/2024 END_DATE=31/01/2024"
	@echo ""
	@echo "  transform        Run the transformation step"
	@echo "                   Required: START_MONTH=YYYY-MM END_MONTH=YYYY-MM"
	@echo "                   Example:  make transform START_MONTH=2024-01 END_MONTH=2024-03"
	@echo ""
	@echo "  dagster-dev      Start the Dagster UI at http://localhost:3000"
	@echo ""
	@echo "Tests"
	@echo "  test             Run unit tests (no Docker required)"
	@echo "  test-unit        Same as test"
	@echo "  test-integration Run integration tests (requires running containers)"
	@echo ""

# ── Dependencies ──────────────────────────────────────────────────────────────
install:
	poetry install

# ── Infrastructure ────────────────────────────────────────────────────────────
up:
	docker compose up -d

down:
	docker compose down

restart: down up

logs:
	docker compose logs -f

reset-db:
	@echo "WARNING: This will delete all data in MongoDB and MinIO."
	@echo "Run 'make reset-db-confirm' to proceed."

reset-db-confirm:
	docker compose down
	rm -rf mongo_data minio_data && mkdir mongo_data minio_data
	docker compose up -d

# ── Scraping ──────────────────────────────────────────────────────────────────
# Env vars are sourced from .env via the include above.
# Override on the command line: make scrape START_DATE=01/01/2024 END_DATE=31/01/2024
scrape:
ifndef START_DATE
	$(error START_DATE is required. Usage: make scrape START_DATE=DD/MM/YYYY END_DATE=DD/MM/YYYY)
endif
ifndef END_DATE
	$(error END_DATE is required. Usage: make scrape START_DATE=DD/MM/YYYY END_DATE=DD/MM/YYYY)
endif
	# PYTHONPATH is required because the Scrapy item pipeline (LandingZonePipeline)
	# imports from app/ (repositories, storage). The spider itself is self-contained.
	cd scrapy_project && PYTHONPATH=$(CURDIR) poetry run scrapy crawl workplace_relations \
		-a start_date="$(START_DATE)" \
		-a end_date="$(END_DATE)" \
		$(if $(BODIES),-a bodies="$(BODIES)",)

# ── Transformation ────────────────────────────────────────────────────────────
transform:
ifndef START_MONTH
	$(error START_MONTH is required. Usage: make transform START_MONTH=YYYY-MM END_MONTH=YYYY-MM)
endif
ifndef END_MONTH
	$(error END_MONTH is required. Usage: make transform START_MONTH=YYYY-MM END_MONTH=YYYY-MM)
endif
	PYTHONPATH=$(CURDIR) poetry run python -m app.services.transformation_service \
		--start-date "$(START_MONTH)" \
		--end-date "$(END_MONTH)"

# ── Dagster UI ────────────────────────────────────────────────────────────────
# PYTHONPATH is set so Dagster can import the app/ package when loading assets.
dagster-dev:
	PYTHONPATH=$(CURDIR) poetry run dagster dev

# ── Tests ─────────────────────────────────────────────────────────────────────
test: test-unit

test-unit:
	poetry run pytest tests/unit/ -v

test-integration:
	poetry run pytest tests/integration/ -v
