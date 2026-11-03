import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv


REPO_DIR = Path(__file__).resolve().parent.parent
load_dotenv(REPO_DIR / ".env", override=False)

RESULTS_DIR = REPO_DIR / "test-results"
KARATE_DIR = REPO_DIR / "karate-runner"
KARATE_FEATURE = (
    KARATE_DIR / "src" / "test" / "resources" / "features" / "generated.feature"
)
KARATE_REPORT_DIR = KARATE_DIR / "target" / "karate-reports"


def redact_secrets(text):
    """Remove known secret values from captured output."""
    text = str(text or "")

    for name in ("TEST_PASSWORD", "GROQ_API_KEY", "JIRA_API_TOKEN",
                 "GITHUB_TOKEN", "JIRA_WEBHOOK_SECRET"):
        value = os.getenv(name)
        if value:
            text = text.replace(value, "<redacted>")

    return text


def write_log(log_path, content):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    safe_content = redact_secrets(content)
    log_path.write_text(safe_content, encoding="utf-8")
    return safe_content


def failure_excerpt(output, max_chars=6000):
    """Return a useful, bounded excerpt for PR comments."""
    output = redact_secrets(output).strip()

    if not output:
        return "No output was captured."

    if len(output) > max_chars:
        output = (
            output[-max_chars:]
            + "\n\n[Earlier output omitted. See full test log artifact.]"
        )

    return output


def run_suite(name, command, log_path, cwd=REPO_DIR):
    """Run one suite and preserve output, including failures and timeouts."""
    started = time.time()

    display_command = [
        "-DTEST_PASSWORD=<redacted>"
        if str(arg).startswith("-DTEST_PASSWORD=")
        else str(arg)
        for arg in command
    ]

    print(
        f"\n{'=' * 70}\n"
        f"Running {name}\n"
        f"Command: {' '.join(display_command)}"
    )

    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            errors="replace",
            timeout=600,
            check=False,
        )

        output = result.stdout or ""
        exit_code = result.returncode
        status = "PASS" if exit_code == 0 else "FAIL"

    except subprocess.TimeoutExpired as exc:
        captured = exc.stdout or ""
        if isinstance(captured, bytes):
            captured = captured.decode("utf-8", errors="replace")

        output = (
            "Test suite timed out after 600 seconds.\n"
            + captured
        )
        exit_code = 124
        status = "FAIL"

    except OSError as exc:
        output = f"Could not start command: {exc}\n"
        exit_code = 127
        status = "ERROR"

    output = write_log(log_path, output)

    print(output, end="" if output.endswith("\n") else "\n")

    result_data = {
        "suite": name,
        "status": status,
        "exit_code": exit_code,
        "duration_seconds": round(time.time() - started, 2),
        "log": str(log_path.relative_to(REPO_DIR)),
        "failure_excerpt": (
            failure_excerpt(output)
            if status != "PASS"
            else ""
        ),
    }

    return result_data


def api_error_result(output_dir, message, exit_code=2):
    """Create a consistent API error result and log."""
    log_path = output_dir / "api.log"
    output = write_log(log_path, message)

    return {
        "suite": "API",
        "status": "ERROR",
        "exit_code": exit_code,
        "duration_seconds": 0,
        "log": str(log_path.relative_to(REPO_DIR)),
        "failure_excerpt": failure_excerpt(output),
    }


def run_api_suite(api_file, output_dir):
    """Run Karate while restoring the original Maven feature file."""
    if not api_file.exists():
        return api_error_result(
            output_dir,
            f"API feature file not found: {api_file}",
        )

    if not (KARATE_DIR / "pom.xml").exists():
        return api_error_result(
            output_dir,
            f"Maven project not found: {KARATE_DIR}",
        )

    mvn = shutil.which("mvn")
    if not mvn:
        return api_error_result(
            output_dir,
            "Maven was not found on PATH.",
            127,
        )

    required = ["BASE_URL", "TEST_USERNAME", "TEST_PASSWORD"]
    missing = [name for name in required if not os.getenv(name)]

    if missing:
        return api_error_result(
            output_dir,
            "Missing environment variables: " + ", ".join(missing),
        )

    KARATE_FEATURE.parent.mkdir(parents=True, exist_ok=True)

    original_exists = KARATE_FEATURE.exists()
    original_content = (
        KARATE_FEATURE.read_bytes() if original_exists else None
    )

    if KARATE_REPORT_DIR.exists():
        shutil.rmtree(KARATE_REPORT_DIR)

    try:
        shutil.copy2(api_file, KARATE_FEATURE)

        command = [
            mvn,
            "test",
            f"-DBASE_URL={os.getenv('BASE_URL')}",
            f"-DTEST_USERNAME={os.getenv('TEST_USERNAME')}",
            f"-DTEST_PASSWORD={os.getenv('TEST_PASSWORD')}",
        ]

        result = run_suite(
            "API",
            command,
            output_dir / "api.log",
            cwd=KARATE_DIR,
        )

        if KARATE_REPORT_DIR.exists():
            destination = output_dir / "karate-reports"
            shutil.copytree(
                KARATE_REPORT_DIR,
                destination,
                dirs_exist_ok=True,
            )

            report = destination / "karate-summary.html"
            if report.exists():
                result["html_report"] = str(
                    report.relative_to(REPO_DIR)
                )

        return result

    finally:
        if original_exists:
            KARATE_FEATURE.write_bytes(original_content)
        elif KARATE_FEATURE.exists():
            KARATE_FEATURE.unlink()


def get_current_git_commit():
    """Return the current Git commit hash."""
    git = shutil.which("git")

    if not git:
        raise RuntimeError("Git was not found on PATH.")

    result = subprocess.run(
        [git, "rev-parse", "HEAD"],
        cwd=REPO_DIR,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Could not determine Git commit: {result.stderr}"
        )

    return result.stdout.strip()


def write_summary(summary, output_dir):
    """Persist summary even when one or more suites fail."""
    summary_path = output_dir / "summary.json"

    summary["summary_path"] = str(
        summary_path.relative_to(REPO_DIR)
    )

    summary_path.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    return summary


def run_ticket_tests(issue_key, run_ui=True, run_api=True):
    """Run selected UI/API suites and save all available evidence."""
    issue_key = issue_key.upper()

    if not all(c.isalnum() or c == "-" for c in issue_key):
        raise ValueError("Invalid Jira issue key.")

    if not run_ui and not run_api:
        raise ValueError("At least one test suite must be selected.")

    issue_dir = REPO_DIR / "generated_tests" / issue_key
    ui_file = issue_dir / "test_ui.py"
    api_file = issue_dir / "test_api.feature"

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    output_dir = RESULTS_DIR / issue_key / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    summary = {
        "issue_key": issue_key,
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "repository": str(REPO_DIR),
        "git_commit": get_current_git_commit(),
        "evidence_dir": str(output_dir.relative_to(REPO_DIR)),
        "suites": [],
    }

    try:
        if run_ui:
            if not ui_file.exists():
                summary["suites"].append({
                    "suite": "UI",
                    "status": "ERROR",
                    "exit_code": 2,
                    "duration_seconds": 0,
                    "failure_excerpt": (
                        f"Requested UI test file not found: {ui_file}"
                    ),
                })
            else:
                junit_file = output_dir / "pytest-report.xml"

                ui_result = run_suite(
                    "UI",
                    [
                        sys.executable,
                        "-m",
                        "pytest",
                        "-v",
                        "--tb=short",
                        "--junitxml",
                        str(junit_file),
                        str(ui_file),
                    ],
                    output_dir / "ui.log",
                )

                if junit_file.exists():
                    ui_result["junit_report"] = str(
                        junit_file.relative_to(REPO_DIR)
                    )

                summary["suites"].append(ui_result)

        if run_api:
            summary["suites"].append(
                run_api_suite(api_file, output_dir)
            )

    except Exception as exc:
        summary["runner_error"] = redact_secrets(str(exc))
        summary["suites"].append({
            "suite": "RUNNER",
            "status": "ERROR",
            "exit_code": 1,
            "duration_seconds": 0,
            "failure_excerpt": failure_excerpt(str(exc)),
        })

    statuses = [
        suite["status"]
        for suite in summary["suites"]
    ]

    summary["overall_status"] = (
        "PASS"
        if statuses and all(status == "PASS" for status in statuses)
        else "FAIL"
        if "FAIL" in statuses
        else "ERROR"
    )

    summary["finished_at_utc"] = datetime.now(
        timezone.utc
    ).isoformat()

    summary = write_summary(summary, output_dir)

    print("\n" + "=" * 70)
    print("SUITE RESULTS")

    for suite in summary["suites"]:
        print(f"  {suite['suite']}: {suite['status']}")

    print(f"\nOverall: {summary['overall_status']}")
    print(f"Evidence folder: {output_dir}")
    print(f"Summary: {output_dir / 'summary.json'}")

    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Run local UI and API automation for a Jira ticket."
    )

    parser.add_argument("issue_key", help="Jira key, e.g. SCRUM-2")
    parser.add_argument("--ui-only", action="store_true")
    parser.add_argument("--api-only", action="store_true")

    args = parser.parse_args()

    if args.ui_only and args.api_only:
        parser.error("Choose at most one of --ui-only or --api-only.")

    try:
        summary = run_ticket_tests(
            issue_key=args.issue_key,
            run_ui=not args.api_only,
            run_api=not args.ui_only,
        )
    except Exception as error:
        print(f"Test runner failed: {error}")
        return 1

    return 0 if summary["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())