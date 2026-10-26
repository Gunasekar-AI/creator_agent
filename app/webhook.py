
import os
import hmac
import hashlib

from fastapi import FastAPI, BackgroundTasks, HTTPException, Request

from app.jira_reader import JiraReader
from app.test_generator import generate_scripts

app = FastAPI()


def process_jira_issue(issue_key):
    # Fetch the latest issue from Jira
    jira = JiraReader()
    ticket = jira.get_ticket(issue_key)

    # AI analyzes the test plan and generates scripts
    generate_scripts(ticket)


@app.post("/webhook/jira")
async def jira_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
):
    # Read the exact body Jira signed
    body = await request.body()

    # Get the webhook secret from .env
    secret = os.getenv("JIRA_WEBHOOK_SECRET")

    # Jira sends the HMAC signature in this header
    signature_header = request.headers.get("X-Hub-Signature", "")

    if not secret or not signature_header:
        raise HTTPException(
            status_code=401,
            detail="Missing webhook secret or signature",
        )

    # Jira signature format: sha256=<hex digest>
    try:
        method, received_signature = signature_header.split("=", 1)
    except ValueError:
        raise HTTPException(
            status_code=401,
            detail="Invalid signature format",
        )

    # This implementation supports SHA-256
    if method.lower() != "sha256":
        raise HTTPException(
            status_code=401,
            detail="Unsupported signature method",
        )

    # Calculate the expected signature
    expected_signature = hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()

    # Compare securely
    if not hmac.compare_digest(
        expected_signature,
        received_signature,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid webhook signature",
        )

    # Parse the verified JSON payload
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON payload",
        )

    issue_key = payload.get("issue", {}).get("key")

    if not issue_key:
        raise HTTPException(
            status_code=400,
            detail="Missing Jira issue key",
        )

    # Process after acknowledging the webhook
    background_tasks.add_task(
        process_jira_issue,
        issue_key,
    )

    return {
        "status": "accepted",
        "issue_key": issue_key,
    }
