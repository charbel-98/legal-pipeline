from datetime import date

from legal_pipeline.application.services.partition_service import build_monthly_partitions


def test_build_monthly_partitions() -> None:
    partitions = build_monthly_partitions(date(2024, 1, 15), date(2024, 3, 5))

    assert len(partitions) == 3
    assert partitions[0].start_date == date(2024, 1, 15)
    assert partitions[0].end_date == date(2024, 1, 31)
    assert partitions[1].partition_date == "2024-02-01"
    assert partitions[2].end_date == date(2024, 3, 5)
