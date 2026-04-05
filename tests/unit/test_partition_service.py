from app.services.partition_service import month_partitions_from_strings, partition_labels


def test_single_month():
    labels = partition_labels("01/01/2024", "31/01/2024")
    assert labels == ["2024-01"]


def test_three_months():
    labels = partition_labels("01/01/2024", "31/03/2024")
    assert labels == ["2024-01", "2024-02", "2024-03"]


def test_cross_year():
    labels = partition_labels("01/12/2023", "31/01/2024")
    assert labels == ["2023-12", "2024-01"]


def test_partitions_have_correct_month_boundaries():
    partitions = list(month_partitions_from_strings("01/01/2024", "28/02/2024"))
    assert len(partitions) == 2
    jan_start, jan_end = partitions[0]
    assert jan_start.day == 1
    assert jan_end.day == 31
    feb_start, feb_end = partitions[1]
    assert feb_start.day == 1
    assert feb_end.day == 28  # 2024 is a leap year but end arg clamps to 28
