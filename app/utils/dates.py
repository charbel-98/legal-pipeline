"""Date parsing helpers."""

from __future__ import annotations

from datetime import date, datetime


def parse_dd_mm_yyyy(raw: str) -> date:
    """Parse a DD/MM/YYYY string into a datetime.date."""
    return datetime.strptime(raw.strip(), "%d/%m/%Y").date()


def parse_yyyy_mm(raw: str) -> date:
    """Parse a YYYY-MM string into the first day of that month."""
    return datetime.strptime(raw.strip(), "%Y-%m").date()
