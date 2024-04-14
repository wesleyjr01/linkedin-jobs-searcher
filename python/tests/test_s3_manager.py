from python_package.lambda_function import S3Manager
import boto3
import pytest


@pytest.mark.freeze_time("2017-05-21 01:02:03.005")
def test_partition_manager():
    s3_manager = S3Manager(
        s3_table_prefix="database1/table1",
        bucket_name="bucket",
        boto3_session=boto3.Session(),
    )

    assert (
        s3_manager.s3_new_file_prefix_with_hourly_partition
        == "database1/table1/ingested_year=2017/ingested_month=05/ingested_day=21/ingested_hour=01/20170521010203005.jsonl"
    )
