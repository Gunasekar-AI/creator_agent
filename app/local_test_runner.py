
from pathlib import Path
import json
import subprocess
import sys
import os
from datetime import datetime, timezone

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def run_ticket_tests(issue_key, run_ui=True, run_api=True):
    """
    Temporary runner.
    Runs requested suites and records their results.
    Replace with the full Karate-integrated runner next.
    """
    evidence_dir = (
        PROJECT_ROOT / "test-results" / issue_key
        / datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    )
    evidence_dir.mkdir(parents=True, exist_ok=True)

    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    suites = []

    if run_ui:
        log_file = evidence_dir / "pytest.log"
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                str(PROJECT_ROOT / "generated_tests" / issue_key / "test_ui.py"),
                "-v",
                "--junitxml",
                str(evidence_dir / "pytest-results.xml"),
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )

        log_file.write_text(
            result.stdout + "\n" + result.stderr,
            encoding="utf-8",
        )

        suites.append({
            "suite": "UI",
            "status": "PASS" if result.returncode == 0 else "FAIL",
            "log": str(log_file),
            "failure_excerpt": result.stderr[-2000:],
        })

    if run_api:
        suites.append({
            "suite": "API",
            "status": "FAIL",
            "log": None,
            "failure_excerpt": (
                "Karate runner is not configured yet. "
                "API tests were not executed."
            ),
        })

    overall_status = (
        "PASS"
        if suites and all(suite["status"] == "PASS" for suite in suites)
        else "FAIL"
    )

    summary = {
        "issue_key": issue_key,
        "git_commit": commit,
        "overall_status": overall_status,
        "suites": suites,
        "evidence_dir": str(evidence_dir),
    }

    (evidence_dir / "summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    return summary
