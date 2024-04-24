import json
import logging
from typing import Dict, List
from linkedin_api import Linkedin
import os
import re
import boto3
import datetime
from ratelimit import limits, sleep_and_retry

# Global Variables / API Rate Limit
period_in_seconds: int = 6
calls_per_period: int = 1


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


class PartitionManager:
    def __init__(self, file_type: str = ".jsonl") -> None:
        self._current_timestamp = datetime.datetime.now()
        self.file_type = file_type
        self.current_timestamp = self.get_current_timestamp_millisecond_precision
        self.current_year = self.get_current_year
        self.current_month = self.get_current_month
        self.current_day = self.get_current_day
        self.current_hour = self.get_current_hour
        self.partition_prefix = self.get_partition_prefix
        self.file_prefix = self.get_file_prefix

    @property
    def get_current_year(self) -> str:
        return self._current_timestamp.strftime("%Y")

    @property
    def get_current_month(self) -> str:
        return self._current_timestamp.strftime("%m")

    @property
    def get_current_day(self) -> str:
        return self._current_timestamp.strftime("%d")

    @property
    def get_current_hour(self) -> str:
        return self._current_timestamp.strftime("%H")

    @property
    def get_current_timestamp_millisecond_precision(self) -> str:
        return self._current_timestamp.strftime("%Y%m%d%H%M%S%f")[:-3]

    @property
    def get_partition_prefix(self) -> str:
        return (
            f"ingested_year={self.current_year}/"
            + f"ingested_month={self.current_month}/"
            + f"ingested_day={self.current_day}/"
            + f"ingested_hour={self.current_hour}"
        )

    @property
    def get_file_prefix(self) -> str:
        return f"{self.partition_prefix}/{self.current_timestamp}{self.file_type}"


class S3Manager:
    def __init__(
        self,
        s3_table_prefix: str,
        bucket_name: str,
        boto3_session: boto3.Session,
        s3_dump_file_type: str = ".jsonl",
    ) -> None:
        self.bucket_name = bucket_name
        self.s3_dump_file_type = s3_dump_file_type
        self.s3_table_prefix = s3_table_prefix
        self.boto3_session = boto3_session
        self.s3_client = self.boto3_session.client("s3")
        self.s3_new_file_prefix_with_hourly_partition = (
            self.get_s3_new_file_prefix_with_hourly_partition
        )

    @property
    def get_s3_new_file_prefix_with_hourly_partition(self) -> str:
        return (
            self.s3_table_prefix
            + "/"
            + PartitionManager(file_type=self.s3_dump_file_type).file_prefix
        )

    def put_data_to_s3_table_with_hourly_partition_as_jsonlines(
        self,
        data: List[Dict],
    ) -> None:
        if self.s3_dump_file_type != ".jsonl":
            raise NotImplementedError("Only .jsonl file dumps are implemented")
        jsonlines_file = "\n".join(json.dumps(d) for d in data)
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=self.s3_new_file_prefix_with_hourly_partition,
            Body=jsonlines_file,
        )
        logger.info(
            f"Dumped new file to: s3://{self.bucket_name}/{self.s3_new_file_prefix_with_hourly_partition}"
        )


class LinkedinJobParser:
    def __init__(
        self,
        login_email: str,
        login_password: str,
        keywords: str,
        days_old_listed_job: int = 1,
        remote: str = "2",
        location: str = "United States",
        limit: int = 150,
    ) -> None:
        self.keywords = keywords
        self.days_old_listed_job = days_old_listed_job
        self.remote = remote
        self.location = location
        self.limit = limit
        self._login_email = login_email
        self._login_password = login_password
        self._listed_at = self.days_old_listed_job * (24 * 65 * 60)
        self._api_client = self.get_api_client
        self._jobs = self.get_jobs
        self._job_ids = self.get_jobs_ids

    @staticmethod
    def epoch_to_timestamp(epoch_time_ms):
        """Convert Unix epoch time in milliseconds to formatted string timestamp.

        Args:
            epoch_time_ms (int): Unix epoch time in milliseconds.

        Returns:
            str: Timestamp in 'YYYY-MM-DD HH:mm:ss' format.
        """
        epoch_time_s = epoch_time_ms / 1000

        date_time = datetime.datetime.utcfromtimestamp(epoch_time_s)

        formatted_time = date_time.strftime("%Y-%m-%d %H:%M:%S")

        return formatted_time

    @staticmethod
    def epoch_to_date(epoch_time_ms):
        """Convert Unix epoch time in milliseconds to formatted string timestamp.

        Args:
            epoch_time_ms (int): Unix epoch time in milliseconds.

        Returns:
            str: Timestamp in 'YYYY-MM-DD HH:mm:ss' format.
        """
        epoch_time_s = epoch_time_ms / 1000

        date_time = datetime.datetime.utcfromtimestamp(epoch_time_s)

        formatted_date = date_time.strftime("%Y-%m-%d")

        return formatted_date

    @staticmethod
    def export_list_of_dict_as_jsonl(data, filename) -> None:
        with open(filename, "w", encoding="utf-8") as file:
            for item in data:
                json_line = json.dumps(item)
                file.write(json_line + "\n")

    @staticmethod
    def is_word_in_text(word: str, text: str) -> bool:
        # \b around the word ensures that it is a complete word, not part of another word
        return (
            re.search(r"\b" + re.escape(word) + r"\b", text, re.IGNORECASE) is not None
        )

    @property
    def get_api_client(self):
        return Linkedin(self._login_email, self._login_password)

    @property
    def get_jobs(self) -> List:
        jobs = self._api_client.search_jobs(
            keywords=self.keywords,
            remote=self.remote,
            listed_at=self._listed_at,
            location_name=self.location,
            limit=self.limit,
        )
        return jobs

    @property
    def get_jobs_ids(self) -> List:
        jobs_ids_list = [job["trackingUrn"].split(":")[-1] for job in self._jobs]
        logger.info(f"Count Jobs: {len(self._jobs)}")
        return jobs_ids_list

    def get_information_from_job(self, job_dict: Dict) -> Dict:
        job_info = {}
        job_description = job_dict.get("description", {}).get("text")
        job_info["job_id"] = job_dict.get("jobPostingId")
        job_info["job_title"] = job_dict.get("title")
        job_info["company_name"] = (
            job_dict.get("companyDetails", {})
            .get(
                "com.linkedin.voyager.deco.jobs.web.shared.WebCompactJobPostingCompany",
                {},
            )
            .get("companyResolutionResult", {})
            .get("name")
        )
        job_info["work_remote_allowed"] = job_dict.get("workRemoteAllowed")
        job_info["is_irrelevant_title"] = (
            self.is_word_in_text("Pessoa", job_info["job_title"])
            or self.is_word_in_text("Desenvolvedor", job_info["job_title"])
            or self.is_word_in_text("Diversity", job_info["job_title"])
            or self.is_word_in_text("Afirmativa", job_info["job_title"])
            or self.is_word_in_text("Engenheiro", job_info["job_title"])
            or self.is_word_in_text("Full-Stack", job_info["job_title"])
            or self.is_word_in_text("Full Stack", job_info["job_title"])
            or self.is_word_in_text("GCP", job_info["job_title"])
            or self.is_word_in_text("Azure", job_info["job_title"])
            or self.is_word_in_text("DevOps", job_info["job_title"])
            or self.is_word_in_text("Node.js", job_info["job_title"])
        )
        job_info["only_usa"] = (
            self.is_word_in_text(
                "must be legally authorized to work in", job_description
            )
            or self.is_word_in_text("Only", job_info["job_title"])
            or self.is_word_in_text("W2", job_description)
        )
        job_info["is_contract"] = self.is_word_in_text("contract", job_description)
        job_info["is_contractactor"] = self.is_word_in_text(
            "contractor", job_description
        )
        job_info["is_401_present"] = (
            self.is_word_in_text("401", job_description)
            or self.is_word_in_text("401k", job_description)
            or self.is_word_in_text("401K", job_description)
        )
        job_info["is_aws_in_job_description"] = self.is_word_in_text(
            "aws", job_description
        )
        job_info["is_terraform_in_job_description"] = self.is_word_in_text(
            "terraform", job_description
        )
        job_info["is_python_in_job_description"] = self.is_word_in_text(
            "python", job_description
        )
        job_info["is_usd_in_job_description"] = self.is_word_in_text(
            "usd", job_description
        )
        job_info["is_clt_in_job_description"] = self.is_word_in_text(
            "CLT", job_description
        )
        job_info["company_apply_url"] = job_dict.get("applyMethod", {}).get(
            "com.linkedin.voyager.jobs.ComplexOnsiteApply", {}
        ).get("companyApplyUrl") or job_dict.get("applyMethod", {}).get(
            "com.linkedin.voyager.jobs.OffsiteApply", {}
        ).get(
            "companyApplyUrl"
        )
        job_info["easy_apply_url"] = (
            job_dict.get("applyMethod", {})
            .get("com.linkedin.voyager.jobs.ComplexOnsiteApply", {})
            .get("easyApplyUrl")
        )
        job_info["formatted_location"] = job_dict.get("formattedLocation")
        job_info["listed_at_timestamp"] = self.epoch_to_timestamp(
            job_dict.get("listedAt", 0)
        )
        job_info["listed_at_date"] = self.epoch_to_date(job_dict.get("listedAt", 0))
        job_info["job_description"] = job_description
        return job_info

    @sleep_and_retry
    @limits(
        calls=calls_per_period,
        period=period_in_seconds,
    )
    def get_job(self, job_id: int) -> Dict:
        return self._api_client.get_job(job_id)

    def get_list_of_parsed_jobs(self) -> List[Dict]:
        list_of_parsed_jobs = []
        logger.info(f"job ids: {self._job_ids}")
        for job_id in self._job_ids:
            job_dict = self.get_job(job_id)
            jobs_info = self.get_information_from_job(job_dict)
            logger.info("Retrieving info from job: %s", jobs_info["job_id"])
            list_of_parsed_jobs.append(jobs_info)
        return list_of_parsed_jobs


def run_glue_crawler(crawler_name: str, boto3_session: boto3.Session) -> None:
    glue_client = boto3_session.client("glue")
    glue_client.start_crawler(Name=crawler_name)
    logger.info(f"Glue Crawler {crawler_name} started")


def lambda_handler(event, context):

    # Get environment variables
    linkedin_email = os.environ["linkedin_email"]
    linkedin_password = os.environ["linkedin_password"]
    linkedin_bucket = os.environ["linkedin_bucket"]
    linkedin_jobs_table_prefix = os.environ["linkedin_jobs_table_prefix"]
    aws_region = os.environ["aws_region"]
    job_search_keywords = os.environ["job_search_keywords"]
    job_search_remote = os.environ["job_search_remote"]
    job_search_location = os.environ.get("job_search_location", None)
    jobs_search_days_old_listed_job = int(os.environ["jobs_search_days_old_listed_job"])
    boto3_session = boto3.Session(region_name=aws_region)

    # Get Linkedin Data
    jobs_searcher = LinkedinJobParser(
        login_email=linkedin_email,
        login_password=linkedin_password,
        keywords=job_search_keywords,
        remote=job_search_remote,
        location=job_search_location,
        days_old_listed_job=jobs_search_days_old_listed_job,
    )
    jobs_info = jobs_searcher.get_list_of_parsed_jobs()

    # Dump Linkedin Data to S3
    s3_manager = S3Manager(
        s3_table_prefix=linkedin_jobs_table_prefix,
        bucket_name=linkedin_bucket,
        boto3_session=boto3_session,
    )
    s3_manager.put_data_to_s3_table_with_hourly_partition_as_jsonlines(jobs_info)

    # Start Glue Crawler
    run_glue_crawler("linkedin-jobs", boto3_session)

    return {"statusCode": 200}


if __name__ == "__main__":
    # env variables
    try:
        from dotenv import load_dotenv

        load_dotenv()
        logger.info(f"Executing in local machine")
        lambda_handler({}, {})
    except Exception as e:
        logger.error(f"Error loading .env file: {e}")
        logger.error(f"Executing in AWS Environment")
