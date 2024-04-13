from typing import Dict
from linkedin_api import Linkedin

from dotenv import load_dotenv
import os
import json

import datetime


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

    @property
    def get_api_client(self):
        return Linkedin(self._login_email, self._login_password)

    @staticmethod
    def epoch_to_timestamp(epoch_time_ms):
        """Convert Unix epoch time in milliseconds to formatted string timestamp.

        Args:
            epoch_time_ms (int): Unix epoch time in milliseconds.

        Returns:
            str: Timestamp in 'YYYY-MM-DD HH:mm:ss' format.
        """
        # Convert milliseconds to seconds
        epoch_time_s = epoch_time_ms / 1000

        # Convert epoch time to a datetime object in UTC
        date_time = datetime.datetime.utcfromtimestamp(epoch_time_s)

        # Format the datetime object as a string in the specified format
        formatted_time = date_time.strftime("%Y-%m-%d %H:%M:%S")

        return formatted_time

    def get_information_from_job(self, job_dict: Dict) -> Dict:
        job_info = {}
        job_info["job_id"] = job_dict["jobPostingId"]
        job_info["company_name"] = (
            job_dict["companyDetails"]
            .get(
                "com.linkedin.voyager.deco.jobs.web.shared.WebCompactJobPostingCompany"
            )
            .get("companyResolutionResult")
            .get("name")
        )
        job_info["job_description"] = job_dict["description"].get("text")
        job_info["job_title"] = job_dict["title"]
        job_info["work_remote_allowed"] = job_dict["workRemoteAllowed"]
        job_info["company_apply_url"] = (
            job_dict["applyMethod"]
            .get("com.linkedin.voyager.jobs.ComplexOnsiteApply")
            .get("companyApplyUrl")
        )
        job_info["easy_apply_url"] = (
            job_dict["applyMethod"]
            .get("com.linkedin.voyager.jobs.ComplexOnsiteApply")
            .get("easyApplyUrl")
        )
        job_info["formatted_location"] = job_dict["formattedLocation"]
        job_info["listed_at"] = self.epoch_to_timestamp(job_dict["listedAt"])
        return job_info

    def get_jobs(self) -> Dict:
        jobs = self._api_client.search_jobs(
            keywords=self.keywords,
            remote=self.remote,
            listed_at=self._listed_at,
        )
        return jobs


if __name__ == "__main__":
    # env variables
    load_dotenv()
    email = os.getenv("email")
    password = os.getenv("password")
    json_filename_export = "jobs.json"

    jobs_searcher = LinkedinJobParser(
        login_email=email,
        login_password=password,
        keywords="Data Engineer",
        days_old_listed_job=2,
    )

    jobs = jobs_searcher.get_jobs()

    # Create dict of values for jobs_list
    # jobs_dict = {f"{index}": value for index, value in enumerate(jobs)}
    # with open(json_filename_export, "w", encoding="utf-8") as f:
    #     json.dump(jobs_dict, f, ensure_ascii=False, indent=4)

    # get one particular job
    # job = api.get_job("3894466400")
    # job_info = get_information_from_job(job)
    # with open("one_job_info.json", "w", encoding="utf-8") as f:
    #     json.dump(job_info, f, ensure_ascii=False, indent=4)
