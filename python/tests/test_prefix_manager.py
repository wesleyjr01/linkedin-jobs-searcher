import pytest
from python_package.lambda_function import PartitionManager


@pytest.mark.freeze_time("2017-05-21 01:02:03.005")
def test_partition_manager():
    partition_manager = PartitionManager(file_type=".jsonl")
    assert partition_manager.current_year == "2017"
    assert partition_manager.current_month == "05"
    assert partition_manager.current_day == "21"
    assert partition_manager.current_hour == "01"
    assert partition_manager.current_timestamp == "20170521010203005"
    assert (
        partition_manager.partition_prefix
        == "ingested_year=2017/ingested_month=05/ingested_day=21/ingested_hour=01"
    )
    assert (
        partition_manager.file_prefix
        == "ingested_year=2017/ingested_month=05/ingested_day=21/ingested_hour=01/20170521010203005.jsonl"
    )
