import json
import sys

from jira_reader import JiraReader

# JIRA_URL ="https://knackforge-team-cbvy7zk3.atlassian.net"
# JIRA_EMAIL ="gunasekar.r@knackforge.com"
# JIRA_API ="ATATT3xFfGF0j_iVRq7T2LNqAAnecwS6TD2xtjF611U2VTyyoiyPCUftV76oOkhfEsD7lmxcJRoq5fpLggBm2PKsY-13qKHp62wVdLa_tnNxI83cenPITvBC0U-NG6D5HVrbQ2qgAMDGn4sh_ZUMQgXOvHOQ4qW2-ggGZVPGoA4Lt_fjPEC6vOw=6D4AE8AA"


def main():

    if len(sys.argv) < 2:
        print("Usage: python app/main.py ISSUE-KEY")
        return

    issue_key = sys.argv[1]

    jira = JiraReader()

    try:
        ticket = jira.get_ticket(issue_key)

        print("\nJira Ticket Retrieved Successfully\n")

        print(json.dumps(
            ticket,
            indent=2,
            ensure_ascii=False
        ))

    except Exception as error:
        print(f"Failed to retrieve Jira ticket: {error}")


if __name__ == "__main__":
    main()