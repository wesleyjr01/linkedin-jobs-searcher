from typing import Dict
from linkedin_api import Linkedin

from dotenv import load_dotenv
import os
import json

import datetime


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


def get_information_from_job(job_dict: Dict) -> Dict:
    job_info = {}
    job_info["job_id"] = job_dict["jobPostingId"]
    job_info["company_name"] = (
        job_dict["companyDetails"]
        .get("com.linkedin.voyager.deco.jobs.web.shared.WebCompactJobPostingCompany")
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
    job_info["listed_at"] = epoch_to_timestamp(job_dict["listedAt"])
    return job_info


# env variables
load_dotenv()
email = os.getenv("email")
password = os.getenv("password")
json_filename_export = "jobs.json"
days_old_listed_job = 2
listed_at = days_old_listed_job * 24 * 60 * 60

if __name__ == "__main__":

    # Authenticate using any Linkedin account credentials
    api = Linkedin(email, password)

    # GET a profile
    jobs = api.search_jobs(
        keywords="data engineer",
        remote="2",
        listed_at=listed_at,
    )

    # Create dict of values for jobs_list
    # jobs_dict = {f"{index}": value for index, value in enumerate(jobs)}
    # with open(json_filename_export, "w", encoding="utf-8") as f:
    #     json.dump(jobs_dict, f, ensure_ascii=False, indent=4)

    # get one particular job
    job = api.get_job("3894466400")
    job_info = get_information_from_job(job)
    with open("one_job_info.json", "w", encoding="utf-8") as f:
        json.dump(job_info, f, ensure_ascii=False, indent=4)
