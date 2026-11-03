
import os
import hmac
import hashlib
import json
import logging
from pathlib import Path
import shutil
import tempfile

from fastapi import FastAPI, BackgroundTasks, HTTPException, Request

from app.jira_reader import JiraReader
from app.test_generator import generate_scripts
from app.local_test_runner import run_ticket_tests
from app.git_publisher import (
    create_or_reuse_pr,
    ensure_github_cli,
    get_changed_paths,
    make_branch_name,
    path_is_inside,
    prepare_generated_tests,
    publish_tested_branch,
    run_git,
)

app = FastAPI()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def get_requested_test_layers(issue_key):
    """Determine which test suites were generated for this Jira issue."""
    cases_file = (
        PROJECT_ROOT / "generated_tests" / issue_key / "test_cases.json"
    )

    if not cases_file.exists():
        raise RuntimeError(f"Test cases file not found: {cases_file}")

    data = json.loads(cases_file.read_text(encoding="utf-8"))
    cases = data.get("test_cases", [])

    test_types = {
        str(case.get("test_type", "")).strip().lower()
        for case in cases
    }

    run_ui = "ui" in test_types
    run_api = "api" in test_types

    if not run_ui and not run_api:
        raise RuntimeError(
            f"No supported UI or API test cases found for {issue_key}."
        )

    return run_ui, run_api


def process_jira_issue(issue_key):
    """Generate, test locally, and publish only after all requested tests pass."""
    try:
        logger.info("Starting automation for %s", issue_key)

        # 1. Fetch Jira issue.
        jira = JiraReader()
        ticket = jira.get_ticket(issue_key)

        if not isinstance(ticket, dict):
            raise RuntimeError("JiraReader returned an unexpected ticket format.")

        # 2. Generate UI/API tests.
        generate_scripts(ticket)

        output_dir = PROJECT_ROOT / "generated_tests" / issue_key
        if not output_dir.is_dir():
            raise RuntimeError(f"Generated output not found: {output_dir}")

        run_ui, run_api = get_requested_test_layers(issue_key)

        logger.info(
            "Requested test layers for %s: UI=%s, API=%s",
            issue_key,
            run_ui,
            run_api,
        )

        # 3. Prepare the Jira branch and commit generated files locally.
        labels = ticket.get("labels", [])
        if not isinstance(labels, list):
            labels = [labels] if labels else []

        prepared = prepare_generated_tests(
            issue_key=issue_key,
            labels=labels,
            output_dir=output_dir,
            repo_dir=PROJECT_ROOT,
            base_branch=os.getenv("GIT_BASE_BRANCH", "main"),
        )

        logger.info(
            "Prepared branch %s at commit %s",
            prepared["branch"],
            prepared["commit"],
        )

        # 4. Run the requested test suites against the prepared commit.
        test_summary = run_ticket_tests(
            issue_key=issue_key,
            run_ui=run_ui,
            run_api=run_api,
        )

        logger.info(
            "Test result for %s: %s",
            issue_key,
            test_summary.get("overall_status"),
        )

        # 5. Verify that the tested commit is exactly the prepared commit.
        if test_summary.get("git_commit") != prepared["commit"]:
            raise RuntimeError(
                "Tested commit does not match the prepared commit. "
                "Refusing to publish."
            )

        # 6. Never push or create a PR when a requested suite fails.
        if test_summary.get("overall_status") != "PASS":
            logger.error(
                "Tests failed for %s. No push or PR publication will occur. "
                "Evidence: %s",
                issue_key,
                test_summary.get("evidence_dir"),
            )

            for suite in test_summary.get("suites", []):
                logger.error(
                    "%s: %s. Log: %s. Details: %s",
                    suite.get("suite"),
                    suite.get("status"),
                    suite.get("log"),
                    suite.get("failure_excerpt", ""),
                )

            return

        # 7. Publish only after all requested suites pass.
        publication = publish_tested_branch(
            prepared=prepared,
            test_summary=test_summary,
            issue_key=issue_key,
            summary=ticket.get("summary", ""),
            repo_dir=PROJECT_ROOT,
        )

        logger.info(
            "Automation passed and PR is ready for %s: %s",
            issue_key,
            publication["pr_url"],
        )

    except Exception:
        logger.exception("Automation failed for Jira issue %s", issue_key)


@app.post("/webhook/jira")
async def jira_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
):
    body = await request.body()

    secret = os.getenv("JIRA_WEBHOOK_SECRET")
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

    if not hmac.compare_digest(expected_signature, received_signature):
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

    background_tasks.add_task(process_jira_issue, issue_key)

    return {
        "status": "accepted",
        "issue_key": issue_key,
    }
