from datetime import date
from typing import Any


def parse_iso_date(raw: str) -> date:
    return date.fromisoformat(raw)


def parse_optional_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))
