#!/usr/bin/env python
"""CLI: run the Scrapy spider for a given date range.

Usage:
    python scripts/run_scrape.py --start-date 01/01/2024 --end-date 31/03/2024
"""

import argparse
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from app.services.ingestion_service import run_scrape  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Workplace Relations spider.")
    parser.add_argument("--start-date", required=True, metavar="DD/MM/YYYY")
    parser.add_argument("--end-date", required=True, metavar="DD/MM/YYYY")
    args = parser.parse_args()

    rc = run_scrape(args.start_date, args.end_date)
    raise SystemExit(rc)


if __name__ == "__main__":
    main()
