#!/usr/bin/env python
"""CLI: run the Scrapy spider for a given date range.

Run via the Makefile (which sources .env and sets PYTHONPATH):
    make scrape START_DATE=01/01/2024 END_DATE=31/03/2024
    make scrape START_DATE=01/01/2024 END_DATE=31/01/2024 BODIES="Labour Court"
"""

import argparse
import sys

from app.services.ingestion_service import run_scrape


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Workplace Relations spider.")
    parser.add_argument("--start-date", required=True, metavar="DD/MM/YYYY")
    parser.add_argument("--end-date", required=True, metavar="DD/MM/YYYY")
    parser.add_argument(
        "--bodies",
        metavar="BODY1,BODY2",
        help="Comma-separated list of legal bodies to scrape. Defaults to all four.",
    )
    args = parser.parse_args()

    bodies = [b.strip() for b in args.bodies.split(",")] if args.bodies else None

    result = run_scrape(args.start_date, args.end_date, bodies=bodies)
    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    main()
