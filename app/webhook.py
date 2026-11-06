
import os
import hmac
import hashlib
import json
import logging
from pathlib import Path
import shutil
import tempfile
from datetime import datetime, timezone
from datetime import datetime, timezone

from app.db.repository import persist_generated_artifacts

from app.dev_execution_repository import (
    persist_dev_execution,
    persist_dev_execution_results,
    evaluate_promotion_eligibility,
)
from app.test_summary_parser import parse_junit_counts

from fastapi import FastAPI, BackgroundTasks, HTTPException, Request
from app.test_summary_parser import parse_junit_counts
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

def _get_any_script_id(issue_key: str) -> int:
    """Return any dev_generated_scripts.script_id created for this issue."""
    from sqlalchemy import text
    from app.db.database import SessionLocal

    with SessionLocal() as db:
        row = db.execute(
            text("""
                SELECT s.script_id
                FROM dev_generated_scripts s
                JOIN dev_planner_mapping m
                  ON m.test_case_id = s.test_case_id
                WHERE m.jira_ticket_id = :issue_key
                ORDER BY s.script_id
                LIMIT 1
            """),
            {"issue_key": issue_key},
        ).fetchone()

    if row is None:
        raise RuntimeError(
            f"No dev_generated_scripts row found for {issue_key}."
        )
    return row[0]

def process_jira_issue(issue_key):
    """DEV: generate → persist → prepare → run → persist results → gate → publish."""
    try:
        logger.info("Starting automation for %s", issue_key)

        # 1. Fetch Jira issue.
        jira = JiraReader()
        ticket = jira.get_ticket(issue_key)
        if not isinstance(ticket, dict):
            raise RuntimeError("JiraReader returned an unexpected ticket format.")

        # 2. Generate UI/API tests (writes generated_tests/<issue>/ on disk).
        generate_scripts(ticket)

        output_dir = PROJECT_ROOT / "generated_tests" / issue_key
        if not output_dir.is_dir():
            raise RuntimeError(f"Generated output not found: {output_dir}")

        # 3. Persist DEV planner mappings + generated scripts.
        cases_file = output_dir / "test_cases.json"
        test_cases = json.loads(
            cases_file.read_text(encoding="utf-8")
        ).get("test_cases", [])

        labels = ticket.get("labels", []) or []
        if not isinstance(labels, list):
            labels = [labels]

        branch_name = make_branch_name(issue_key, labels)

        persisted = persist_generated_artifacts(
            issue_key=issue_key,
            test_cases=test_cases,
            output_dir=output_dir,
            git_branch=branch_name,
        )
        logger.info("DEV artifacts persisted: %s", persisted)

        # 4. Determine requested suites + prepare branch.
        run_ui, run_api = get_requested_test_layers(issue_key)
        logger.info(
            "Requested layers for %s: UI=%s API=%s",
            issue_key, run_ui, run_api,
        )

        prepared = prepare_generated_tests(
            issue_key=issue_key,
            labels=labels,
            output_dir=output_dir,
            repo_dir=PROJECT_ROOT,
            base_branch=os.getenv("GIT_BASE_BRANCH", "main"),
        )
        logger.info(
            "Prepared branch %s at commit %s",
            prepared["branch"], prepared["commit"],
        )

        # 5. Run tests.
        test_summary = run_ticket_tests(
            issue_key=issue_key, run_ui=run_ui, run_api=run_api,
        )
        logger.info(
            "Test result for %s: %s",
            issue_key, test_summary.get("overall_status"),
        )

        if test_summary.get("git_commit") != prepared["commit"]:
            raise RuntimeError(
                "Tested commit does not match prepared commit. "
                "Refusing to publish."
            )

                # 6. Persist DEV execution + results.
        #    The runner writes pytest-report.xml (not pytest-results.xml).
        evidence_dir = Path(test_summary["evidence_dir"])
        junit_path = evidence_dir / "pytest-report.xml"
        if not junit_path.exists():
            junit_path = evidence_dir / "pytest-results.xml"  # fallback
        counts = parse_junit_counts(
            Path(test_summary["evidence_dir"]) / "pytest-results.xml"
            )

        # 6a. Guard: 0 tests collected = failing run, do not hit the gate.
        if counts["total"] == 0:
            logger.error(
                "No tests collected for %s. Recording a failing run.",
                issue_key,
            )
            execution_id = persist_dev_execution(
                script_id=_get_any_script_id(issue_key),
                execution_status="FAILED",
                framework_name="pytest",
                execution_type="MANUAL",
                completed_at=datetime.now(timezone.utc),
                rollback_status="not_required",
                error_message="pytest collected 0 tests",
            )
            persist_dev_execution_results(
                execution_id=execution_id,
                total_tests=1, passed_tests=0,
                failed_tests=1, skipped_tests=0,
                result_status="FAIL",
            )
            evaluate_promotion_eligibility(
                execution_id=execution_id,
                total_tests=1, passed_tests=0,
                threshold_value=float(
                    os.getenv("DEV_PROMOTION_THRESHOLD", "95")
                ),
            )
            return

        ui_suite = next(
            (s for s in test_summary.get("suites", []) if s["suite"] == "UI"),
            None,
        )
        if ui_suite is None:
            raise RuntimeError("UI suite not found in test summary.")

        execution_id = persist_dev_execution(
            script_id=_get_any_script_id(issue_key),
            execution_status=(
                "COMPLETED" if ui_suite["status"] == "PASS" else "FAILED"
            ),
            framework_name="pytest",
            execution_type="MANUAL",
            completed_at=datetime.now(timezone.utc),
            rollback_status="not_required",
            error_message=(
                None
                if ui_suite["status"] == "PASS"
                else ui_suite.get("failure_excerpt")
            ),
        )

        result_id = persist_dev_execution_results(
            execution_id=execution_id,
            total_tests=counts["total"],
            passed_tests=counts["passed"],
            failed_tests=counts["failed"],
            skipped_tests=counts["skipped"],
            result_status=(
                "PASS" if ui_suite["status"] == "PASS" else "FAIL"
            ),
        )

        # 7. Promotion gate uses OVERALL run status, not just UI pass%.
        #    API passed here but UI failed → overall FAIL → NOT_ELIGIBLE.
        threshold = float(os.getenv("DEV_PROMOTION_THRESHOLD", "95"))
        overall_pass = test_summary.get("overall_status") == "PASS"
        gate_passed = counts["passed"] if overall_pass else 0

        gate = evaluate_promotion_eligibility(
            execution_id=execution_id,
            total_tests=counts["total"],
            passed_tests=gate_passed,
            threshold_value=threshold,
        )
        logger.info(
            "DEV execution=%s result=%s gate=%s",
            execution_id, result_id, gate,
        )

        # 8. Publish only when tests pass.
        if test_summary.get("overall_status") != "PASS":
            logger.error(
                "Tests failed for %s. No push or PR. Evidence: %s",
                issue_key, test_summary.get("evidence_dir"),
            )
            for suite in test_summary.get("suites", []):
                logger.error(
                    "%s: %s | log=%s | %s",
                    suite.get("suite"), suite.get("status"),
                    suite.get("log"), suite.get("failure_excerpt", ""),
                )
            return

        publication = publish_tested_branch(
            prepared=prepared,
            test_summary=test_summary,
            issue_key=issue_key,
            summary=ticket.get("summary", ""),
            repo_dir=PROJECT_ROOT,
        )
        logger.info(
            "Automation passed and PR ready for %s: %s",
            issue_key, publication["pr_url"],
        )

    except Exception:
        logger.exception("Automation failed for Jira issue %s", issue_key)

def _get_any_script_id(issue_key: str) -> int:
    """Return any dev_generated_scripts.script_id for this issue's test cases."""
    from sqlalchemy import text
    from app.db.database import SessionLocal

    with SessionLocal() as db:
        row = db.execute(
            text("""
                SELECT s.script_id
                FROM dev_generated_scripts s
                JOIN dev_planner_mapping m
                  ON m.test_case_id = s.test_case_id
                 AND m.jira_ticket_id = :issue_key
                ORDER BY s.script_id
                LIMIT 1
            """),
            {"issue_key": issue_key},
        ).fetchone()

    if row is None:
        raise RuntimeError(
            f"No dev_generated_scripts row found for {issue_key}."
        )
    return row[0]

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
