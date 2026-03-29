from dataclasses import asdict
from datetime import date
from typing import Any

from legal_pipeline.domain.entities.record import DocumentRecord


def serialize_record(record: DocumentRecord) -> dict[str, Any]:
    payload = asdict(record)
    record_date = payload.get("record_date")
    if isinstance(record_date, date):
        payload["record_date"] = record_date.isoformat()
    return payload
