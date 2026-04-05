"""Month range generation for pipeline partitioning."""

from __future__ import annotations

from datetime import date
from typing import Iterator

from config.partitions import monthly_partitions, parse_date


def month_partitions_from_strings(
    start: str, end: str, date_fmt: str = "%d/%m/%Y"
) -> Iterator[tuple[date, date]]:
    """Yield (month_start, month_end) tuples from DD/MM/YYYY date strings."""
    return monthly_partitions(parse_date(start), parse_date(end))


def partition_labels(start: str, end: str) -> list[str]:
    """Return list of YYYY-MM partition labels for a date range."""
    return [p_start.strftime("%Y-%m") for p_start, _ in month_partitions_from_strings(start, end)]
