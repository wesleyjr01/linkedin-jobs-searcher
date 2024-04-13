from linkedin_api import Linkedin

from dotenv import load_dotenv
import os
import json

# env variables
load_dotenv()
email = os.getenv("email")
password = os.getenv("password")
json_filename_export = "jobs.json"
days_old_listed_job = 2
listed_at = days_old_listed_job * 24 * 60 * 60

# Authenticate using any Linkedin account credentials
api = Linkedin(email, password)

# GET a profile
jobs = api.search_jobs(
    keywords="data engineer",
    remote="2",
    listed_at=listed_at,
)

# Create dict of values
jobs_dict = {f"{index}": value for index, value in enumerate(jobs)}

print(jobs_dict)
with open(json_filename_export, "w", encoding="utf-8") as f:
    json.dump(jobs_dict, f, ensure_ascii=False, indent=4)
