"""Ingestion service — orchestrates scrape runs via subprocess."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

_SCRAPY_PROJECT_DIR = Path(__file__).parent.parent.parent / "scrapy_project"

_ALL_BODIES = [
    "Employment Appeals Tribunal",
    "Equality Tribunal",
    "Labour Court",
    "Workplace Relations Commission",
]


@dataclass
class ScrapeResult:
    returncode: int
    stored: int = 0
    unchanged: int = 0
    failed: int = 0
    dropped: int = 0
    pages_scraped: int = 0
    elapsed_seconds: float = 0.0
    raw_stats: dict = field(default_factory=dict)

    @property
    def success(self) -> bool:
        return self.returncode == 0


def run_scrape(
    start_date: str,
    end_date: str,
    bodies: list[str] | None = None,
    scrapy_project_dir: Path | None = None,
    log: Callable[[str], None] | None = None,
) -> ScrapeResult:
    """Run the Scrapy spider for a given date range.

    Args:
        start_date: DD/MM/YYYY format.
        end_date: DD/MM/YYYY format.
        bodies: Subset of legal bodies to scrape. Defaults to all 4.
        scrapy_project_dir: Path to scrapy_project/. Defaults to project-relative path.
        log: Logging callable (e.g. context.log.info). Defaults to print.

    Returns:
        ScrapeResult with returncode and pipeline stats.
    """
    log = log or print
    cwd = scrapy_project_dir or _SCRAPY_PROJECT_DIR
    selected_bodies = bodies or _ALL_BODIES

    # Temp file for Scrapy to write stats into after spider closes
    stats_fd, stats_path = tempfile.mkstemp(suffix=".json", prefix="scrapy_stats_")
    os.close(stats_fd)

    cmd = [
        "scrapy", "crawl", "workplace_relations",
        "-a", f"start_date={start_date}",
        "-a", f"end_date={end_date}",
        "-a", f"bodies={','.join(selected_bodies)}",
        "-s", f"STATS_EXPORT_FILE={stats_path}",
    ]

    # Ensure the project root is on PYTHONPATH so that `app` is importable
    # from within the scrapy_project/ subprocess.
    project_root = str(_SCRAPY_PROJECT_DIR.parent)
    env = os.environ.copy()
    env["PYTHONPATH"] = project_root + (f":{env['PYTHONPATH']}" if env.get("PYTHONPATH") else "")

    log(f"Running: {' '.join(cmd)} (cwd={cwd})")
    proc = subprocess.run(cmd, cwd=cwd, env=env, check=False)

    raw_stats: dict = {}
    try:
        with open(stats_path, encoding="utf-8") as fh:
            raw_stats = json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    finally:
        try:
            os.unlink(stats_path)
        except OSError:
            pass

    return ScrapeResult(
        returncode=proc.returncode,
        stored=raw_stats.get("landing_pipeline/stored", 0),
        unchanged=raw_stats.get("landing_pipeline/unchanged", 0),
        failed=raw_stats.get("landing_pipeline/failed", 0),
        dropped=raw_stats.get("item_dropped_count", 0),
        pages_scraped=raw_stats.get("downloader/response_count", 0),
        elapsed_seconds=raw_stats.get("elapsed_time_seconds", 0.0),
        raw_stats=raw_stats,
    )
