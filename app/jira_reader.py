import os

import requests
from dotenv import load_dotenv

load_dotenv()

JIRA_URL ="https://knackforge-team-cbvy7zk3.atlassian.net"
JIRA_EMAIL ="gunasekar.r@knackforge.com"
JIRA_API_TOKEN ="ATATT3xFfGF013gkobRvxunlK2j8EZNoeEDAvJnTb8pNAwzKsNK7iVLW7r3xcEhpJiXzz4j0SDdwAJVjD-zAdDNaGpmiuIqA82yirhBkznQ_J8Ssy3qqCZcLuXt3jOVzwL5bQh3_8BE0t7TA1OsJ43OoA1Xi8REIqfAfUN78OkJL02t4xgfDxbY=7F9631EB"


class JiraReader:

    def __init__(self):
        self.base_url = os.getenv("JIRA_URL")
        self.email = os.getenv("JIRA_EMAIL")
        self.api_token = os.getenv("JIRA_API_TOKEN")

        if not all([self.base_url, self.email, self.api_token]):
            raise ValueError(
                "Missing Jira configuration in .env"
            )

        self.base_url = self.base_url.rstrip("/")

    def get_ticket(self, issue_key):

        url = f"{self.base_url}/rest/api/3/issue/{issue_key}"

        response = requests.get(
            url,
            auth=(self.email, self.api_token),
            headers={"Accept": "application/json"},
            params={
                "fields": "summary,description,issuetype,labels"
            },
            timeout=30
        )
        if not response.ok:
            print("Jira API status:", response.status_code)
            print("Jira API response:", response.text)

        response.raise_for_status()

        issue = response.json()
        fields = issue["fields"]

        return {
            "issue_key": issue["key"],
            "summary": fields.get("summary"),
            "description": fields.get("description"),
            "issue_type": fields.get("issuetype", {}).get("name"),
            "labels": fields.get("labels", [])
        }