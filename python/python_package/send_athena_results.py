import logging
from typing import Dict, List
import boto3
import time
import datetime
import json


# Define logger
def get_logger(
    level: int = logging.INFO,
    format: str = "%(asctime)s [%(filename)s] [%(funcName)s] [%(levelname)s] %(message)s",
    logging_file_handler: str = "/tmp/filename.log",
):
    handlers = [logging.FileHandler(logging_file_handler), logging.StreamHandler()]
    logging.basicConfig(level=level, format=format, handlers=handlers)
    logger = logging.getLogger()
    logger.setLevel(level)
    return logger


logger = get_logger()


def run_athena_query(athena_client, query, database, s3_output) -> str:
    athena = athena_client
    response = athena.start_query_execution(
        QueryString=query,
        QueryExecutionContext={"Database": database},
        ResultConfiguration={"OutputLocation": s3_output},
    )
    logger.info("Query Execution ID: %s", response["QueryExecutionId"])
    return response["QueryExecutionId"]


def check_query_status(athena_client, execution_id):
    athena = athena_client
    while True:
        response = athena.get_query_execution(QueryExecutionId=execution_id)
        status = response["QueryExecution"]["Status"]["State"]
        logger.info(f"Query status: {status}")
        if status in ["SUCCEEDED", "FAILED", "CANCELLED"]:
            return status
        time.sleep(5)


def get_query_results(athena_client, execution_id):
    athena = athena_client
    response = athena.get_query_results(QueryExecutionId=execution_id)
    return response


def send_dict_as_sns_message(sns_client, data, topic_arn):
    # Serialize the dictionary to a JSON string
    logger.info("Sending data to e-mail")
    message = json.dumps(data)
    current_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Send the serialized message
    response = sns_client.publish(
        TopicArn=topic_arn,
        Message=message,
        Subject=f"Linkedin Digest - {current_timestamp}",
    )

    # Return the response
    return response


def parse_result_from_athena_query_into_jsonlines(payload) -> List[Dict]:
    # Extract the Rows from the ResultSet
    rows = payload.get("ResultSet", {}).get("Rows", [])

    # Check if there are rows and extract the header (first row) if possible
    if not rows:
        return []

    # The first row contains column headers
    headers = [column["VarCharValue"] for column in rows[0]["Data"]]

    # Initialize a list to hold all the parsed data
    data_list = []

    # Process each row after the header
    for row in rows[1:]:
        # Extract the data values in order, matching them to the headers
        data_dict = {
            header: data.get("VarCharValue", "")
            for header, data in zip(headers, row["Data"])
        }
        data_list.append(data_dict)

    separator = "                                                                                                                                                                                                              "
    jsonlines_file = separator.join(json.dumps(d) for d in data_list)

    return jsonlines_file


def get_yesterdays_date():
    today = datetime.datetime.now()

    yesterday = today - datetime.timedelta(days=1)

    year = str(yesterday.year)
    month = f"{yesterday.month:02d}"
    day = f"{yesterday.day:02d}"

    return year, month, day


def lambda_handler(event, context):
    # Declare Variables
    boto3_session = boto3.Session(region_name="us-east-1")
    athena_client = boto3_session.client("athena")
    sns_client = boto3_session.client("sns")
    yesterday_year, yesterday_month, yesterday_day = get_yesterdays_date()
    query = f"""
    with cte_dedup_by_job as (
        SELECT *
                ,ROW_NUMBER() OVER (PARTITION BY job_id ORDER BY (SELECT NULL)) as rn_1
                ,ROW_NUMBER() OVER (PARTITION BY job_title, company_name ORDER BY (SELECT NULL)) as rn_2
        FROM linkedin.linkedin_jobs
    )
    select job_id, job_title, company_name, formatted_location, listed_at_timestamp
    from cte_dedup_by_job 
    where (
        rn_1=1 AND 
        rn_2=1 AND
        is_clt_in_job_description=false AND
        is_aws_in_job_description=true AND
        is_python_in_job_description=true AND
        only_usa=false AND
        is_401_present=false
    ) AND (
        CAST(ingested_year as INTEGER) >= {yesterday_year} AND
        CAST(ingested_month as INTEGER) >= {yesterday_month} AND
        CAST(ingested_day as INTEGER) >= {yesterday_day}
    )
    """
    glue_db = "linkedin"
    query_output_path = "s3://linkedin-data-w-2024/athena_results/"
    sns_topic_arn = "arn:aws:sns:us-east-1:657613168245:linkedin-athena-results"

    # Run the query / Get Results
    query_id = run_athena_query(athena_client, query, glue_db, query_output_path)
    check_query_status(athena_client, query_id)
    query_results = get_query_results(athena_client, query_id)
    parsed_query_results = parse_result_from_athena_query_into_jsonlines(query_results)

    # Send the results to SNS
    send_dict_as_sns_message(sns_client, parsed_query_results, sns_topic_arn)

    return "200 Success"


if __name__ == "__main__":
    try:
        from dotenv import load_dotenv

        load_dotenv()
        logger.info(f"Executing in local machine")
        lambda_handler({}, {})
    except Exception as e:
        logger.error(f"Error loading .env file: {e}")
        logger.error(f"Executing in AWS Environment")
