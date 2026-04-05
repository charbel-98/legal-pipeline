"""Ingestion service — orchestrates scrape runs via subprocess."""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path

_SCRAPY_PROJECT_DIR = Path(__file__).parent.parent.parent / "scrapy_project"

_ALL_BODIES = [
    "Employment Appeals Tribunal",
    "Equality Tribunal",
    "Labour Court",
    "Workplace Relations Commission",
]


def run_scrape(
    start_date: str,
    end_date: str,
    bodies: list[str] | None = None,
    scrapy_project_dir: Path | None = None,
    log: Callable[[str], None] | None = None,
) -> int:
    """Run the Scrapy spider for a given date range.

    Args:
        start_date: DD/MM/YYYY format.
        end_date: DD/MM/YYYY format.
        bodies: Subset of legal bodies to scrape. Defaults to all 4.
        scrapy_project_dir: Path to scrapy_project/. Defaults to project-relative path.
        log: Logging callable (e.g. context.log.info). Defaults to print.

    Returns:
        Subprocess return code (0 = success).
    """
    log = log or print
    cwd = scrapy_project_dir or _SCRAPY_PROJECT_DIR
    selected_bodies = bodies or _ALL_BODIES

    cmd = [
        "scrapy", "crawl", "workplace_relations",
        "-a", f"start_date={start_date}",
        "-a", f"end_date={end_date}",
        "-a", f"bodies={','.join(selected_bodies)}",
    ]

    log(f"Running: {' '.join(cmd)} (cwd={cwd})")
    result = subprocess.run(cmd, cwd=cwd, check=False)
    return result.returncode
