from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class DatePartition:
    start_date: date
    end_date: date
    partition_date: str


def build_monthly_partitions(start_date: date, end_date: date) -> list[DatePartition]:
    partitions: list[DatePartition] = []
    current = date(start_date.year, start_date.month, 1)

    while current <= end_date:
        if current.month == 12:
            next_month = date(current.year + 1, 1, 1)
        else:
            next_month = date(current.year, current.month + 1, 1)

        partition_start = max(current, start_date)
        partition_end = min(next_month.fromordinal(next_month.toordinal() - 1), end_date)

        partitions.append(
            DatePartition(
                start_date=partition_start,
                end_date=partition_end,
                partition_date=current.isoformat(),
            )
        )
        current = next_month

    return partitions

