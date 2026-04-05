"""Date partitioning helpers shared across the pipeline."""

from __future__ import annotations

import calendar
from datetime import date, datetime
from typing import Iterator

_DATE_FMT = "%d/%m/%Y"


def parse_date(raw: str) -> date:
    """Parse a DD/MM/YYYY string into a datetime.date."""
    return datetime.strptime(raw.strip(), _DATE_FMT).date()


def monthly_partitions(start: date, end: date) -> Iterator[tuple[date, date]]:
    """Yield (month_start, month_end) tuples covering [start, end] inclusive."""
    current = start.replace(day=1)
    end_month_start = end.replace(day=1)

    while current <= end_month_start:
        last_day = calendar.monthrange(current.year, current.month)[1]
        month_end = min(current.replace(day=last_day), end)
        yield current, month_end

        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1, day=1)
        else:
            current = current.replace(month=current.month + 1, day=1)
