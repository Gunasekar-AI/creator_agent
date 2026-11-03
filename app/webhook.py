import os
import hmac
import hashlib
import logging
from pathlib import Path
import json

from fastapi import FastAPI, BackgroundTasks, HTTPException, Request

from app.change_detector import (
    detect_ticket_change,
    save_ticket_snapshot,
)
from app.local_test_runner import run_ticket_tests
from app.git_publisher import (
    prepare_generated_tests,
    publish_tested_branch,
    add_test_failure_comment,
)
from app.jira_reader import JiraReader
from app.test_generator import generate_scripts



app = FastAPI()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def process_jira_issue(issue_key):
    """Generate, test, and publish Jira automation safely."""

    try:
        logger.info("Starting automation for %s", issue_key)

        # 1. Retrieve the Jira ticket.
        jira = JiraReader()
        ticket = jira.get_ticket(issue_key)

        # 2. Detect whether the ticket has changed.
        change = detect_ticket_change(ticket)
        status = change["status"]

        logger.info("Ticket change status: %s", status)

        if status == "unchanged":
            logger.info("No changes detected. Skipping %s.", issue_key)
            return

        if status == "changed":
            logger.info(
                "Ticket changed. Full regeneration will be used "
                "until targeted incremental patching is implemented."
            )

        
        # 3. Generate tests locally. Never publish from the generator.
        generated = generate_scripts(ticket)

        issue_output = PROJECT_ROOT / "generated_tests" / issue_key

        # Determine requested test layers from extracted Jira cases.
        extracted_path = issue_output / "test_cases.json"

        if not extracted_path.exists():
            raise RuntimeError("Extracted test cases file is missing.")

        with extracted_path.open("r", encoding="utf-8") as file:
            extracted = json.load(file)

        test_cases = extracted.get("test_cases", [])

        run_ui = any(
            str(case.get("test_type", "")).lower() == "ui"
            for case in test_cases
        )

        run_api = any(
            str(case.get("test_type", "")).lower() == "api"
            for case in test_cases
        )

        if not run_ui and not run_api:
            raise RuntimeError(
                f"No supported UI or API test cases found for {issue_key}."
            )

        # Check only the files required by Jira.
        if run_ui and not (issue_output / "test_ui.py").exists():
            raise RuntimeError("Generated UI test file is missing.")

        if run_api and not (issue_output / "test_api.feature").exists():
            raise RuntimeError("Generated API feature file is missing.")

        logger.info(
            "Requested test layers for %s: UI=%s, API=%s",
            issue_key,
            run_ui,
            run_api,
        )

        # 4. Prepare a local branch and commit.
        prepared = prepare_generated_tests(
            issue_key=issue_key,
            labels=ticket.get("labels", []),
            output_dir=issue_output,
            repo_dir=PROJECT_ROOT,
            base_branch=os.getenv("GITHUB_BASE_BRANCH", "main"),
        )

        logger.info(
            "Prepared branch %s at commit %s",
            prepared["branch"],
            prepared["commit"],
        )

        # 5. Run only the requested test suites.
        test_summary = run_ticket_tests(
            issue_key=issue_key,
            run_ui=run_ui,
            run_api=run_api,
        )

        # 6. Verify the test run is for the exact prepared commit.
        if test_summary.get("git_commit") != prepared["commit"]:
            raise RuntimeError(
                "Tested commit does not match prepared commit. "
                "Refusing to publish."
            )

        if test_summary.get("overall_status") != "PASS":
            logger.error(
                "Tests failed for %s. No push or PR will be created.",
                issue_key,
            )

            try:
                failure_pr = add_test_failure_comment(
                    repo=PROJECT_ROOT,
                    issue_key=issue_key,
                    branch=prepared["branch"],
                    base_branch=prepared["base_branch"],
                    test_summary=test_summary,
                )

                if failure_pr:
                    logger.info(
                        "Failure report posted to existing PR: %s",
                        failure_pr,
                    )
                else:
                    logger.warning(
                        "No existing PR found. Failure evidence is saved locally."
                    )

            except Exception:
                logger.exception(
                    "Could not post failure report for %s",
                    issue_key,
                )

            return

        # 7. Publish only after requested suites pass.
        result = publish_tested_branch(
            issue_key=issue_key,
            prepared=prepared,
            test_summary=test_summary,
            repo_dir=PROJECT_ROOT,
            summary=ticket.get("summary", ""),
        )


        # 8. Save the Jira snapshot only after successful publication.
        save_ticket_snapshot(ticket)

        logger.info(
            "PR successfully published for %s: %s",
            issue_key,
            result["pr_url"],
        )

    except Exception:
        logger.exception(
            "Automation failed for Jira issue %s",
            issue_key,
        )


@app.post("/webhook/jira")
async def jira_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
):
    # Read the exact body Jira signed
    body = await request.body()

    # Get the webhook secret from .env
    secret = os.getenv("JIRA_WEBHOOK_SECRET")

    # Jira signature header
    signature_header = request.headers.get("X-Hub-Signature", "")

    if not secret or not signature_header:
        raise HTTPException(
            status_code=401,
            detail="Missing webhook secret or signature",
        )

    try:
        method, received_signature = signature_header.split("=", 1)
    except ValueError:
        raise HTTPException(
            status_code=401,
            detail="Invalid signature format",
        )

    if method.lower() != "sha256":
        raise HTTPException(
            status_code=401,
            detail="Unsupported signature method",
        )

    expected_signature = hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(
        expected_signature,
        received_signature,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid webhook signature",
        )

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

    # Acknowledge Jira immediately; generation and tests run afterward.
    background_tasks.add_task(process_jira_issue, issue_key)

    return {
        "status": "accepted",
        "issue_key": issue_key,
    }
