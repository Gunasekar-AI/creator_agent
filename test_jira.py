from app.jira_reader import JiraReader
import requests
from requests.auth import HTTPBasicAuth

jira = JiraReader()

auth = HTTPBasicAuth(jira.email, jira.api_token)
headers = {"Accept": "application/json"}

# Check API authentication
me = requests.get(
    f"{jira.base_url}/rest/api/3/myself",
    auth=auth,
    headers=headers,
    timeout=30,
)

print("Authentication check:", me.status_code)

if me.ok:
    account = me.json()
    print("Authenticated Jira account:", account.get("displayName"))
    print("Account ID:", account.get("accountId"))
else:
    print("Authentication response:", me.text)

# Check issue access
issue = requests.get(
    f"{jira.base_url}/rest/api/3/issue/SCRUM-2",
    auth=auth,
    headers=headers,
    timeout=30,
)

print("Issue check:", issue.status_code)

if issue.ok:
    data = issue.json()
    print("Issue key:", data.get("key"))
    print("Summary:", data.get("fields", {}).get("summary"))
else:
    print("Issue response:", issue.text)