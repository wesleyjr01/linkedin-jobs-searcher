import json
import logging
from typing import Dict, List
from linkedin_api import Linkedin

from dotenv import load_dotenv
import os

import datetime
from ratelimit import limits, sleep_and_retry

# Global Variables / API Rate Limit
period_in_seconds: int = 15
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


class LinkedinJobParser:

    def __init__(
        self,
        login_email: str,
        login_password: str,
        keywords: str,
        days_old_listed_job: int = 1,
        remote: str = "2",
    ) -> None:
        self.keywords = keywords
        self.days_old_listed_job = days_old_listed_job
        self.remote = remote
        self._login_email = login_email
        self._login_password = login_password
        self._listed_at = self.days_old_listed_job * 24 * 60 * 60
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

    @property
    def get_api_client(self):
        return Linkedin(self._login_email, self._login_password)

    @property
    def get_jobs(self) -> List:
        jobs = self._api_client.search_jobs(
            keywords=self.keywords,
            remote=self.remote,
            listed_at=self._listed_at,
        )
        return jobs

    @property
    def get_jobs_ids(self) -> List:
        jobs_ids_list = [job["trackingUrn"].split(":")[-1] for job in self._jobs]
        return jobs_ids_list

    def get_information_from_job(self, job_dict: Dict) -> Dict:
        job_info = {}
        job_info["job_id"] = job_dict.get("jobPostingId")
        job_info["company_name"] = (
            job_dict.get("companyDetails", {})
            .get(
                "com.linkedin.voyager.deco.jobs.web.shared.WebCompactJobPostingCompany",
                {},
            )
            .get("companyResolutionResult", {})
            .get("name")
        )
        job_info["job_description"] = job_dict.get("description", {}).get("text")
        job_info["job_title"] = job_dict.get("title")
        job_info["work_remote_allowed"] = job_dict.get("workRemoteAllowed")
        job_info["company_apply_url"] = (
            job_dict.get("applyMethod", {})
            .get("com.linkedin.voyager.jobs.ComplexOnsiteApply", {})
            .get("companyApplyUrl")
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
        return job_info

    @sleep_and_retry
    @limits(
        calls=calls_per_period,
        period=period_in_seconds,
    )
    def get_job(self, job_id: int) -> Dict:
        return self._api_client.get_job(job_id)

    def get_list_of_parsed_jobs(self) -> List:
        list_of_parsed_jobs = []
        logger.info(f"job ids: {self._job_ids}")
        for job_id in self._job_ids:
            job_dict = self.get_job(job_id)
            jobs_info = self.get_information_from_job(job_dict)
            logger.info("Job information: %s", jobs_info)
            list_of_parsed_jobs.append(jobs_info)
        return list_of_parsed_jobs


if __name__ == "__main__":
    # env variables
    load_dotenv()
    email = os.environ.get("email")
    password = os.environ.get("password")

    jobs_searcher = LinkedinJobParser(
        login_email=email,
        login_password=password,
        keywords="Data Engineer",
        days_old_listed_job=2,
    )
    jobs_info = jobs_searcher.get_list_of_parsed_jobs()
    jobs_searcher.export_list_of_dict_as_jsonl(jobs_info, "jobs_info.jsonl")
