
import argparse
import json
import subprocess
import sys
from pathlib import Path


REPO_DIR = Path(__file__).resolve().parent.parent
DEFAULT_BASE_BRANCH = "main"


def run_command(args, check=True):
    """Run a command from the repository root."""
    print("\n>", " ".join(map(str, args)))

    result = subprocess.run(
        args,
        cwd=REPO_DIR,
        text=True,
        capture_output=True,
    )

    if result.stdout:
        print(result.stdout)

    if result.stderr:
        print(result.stderr)

    if check and result.returncode != 0:
        raise RuntimeError(
            f"Command failed with exit code {result.returncode}: {args[0]}"
        )

    return result


def git(*args, check=True):
    return run_command(["git", *args], check=check)


def ensure_clean_worktree():
    """Avoid overwriting local changes when switching branches."""
    result = git(
        "status", "--porcelain", "--untracked-files=all"
    )

    if result.stdout.strip():
        raise RuntimeError(
            "Your working tree has uncommitted changes.\n"
            "Commit or safely stash them before syncing branches."
        )


def show_merged_prs(base_branch):
    """Display merged PRs targeting the requested base branch."""
    result = run_command(
        [
            "gh", "pr", "list",
            "--state", "merged",
            "--base", base_branch,
            "--limit", "100",
            "--json", "number,title,headRefName,mergedAt,url",
        ]
    )

    prs = json.loads(result.stdout or "[]")

    print(f"\nMerged PRs targeting {base_branch}: {len(prs)}")

    for pr in prs:
        print(
            f"#{pr['number']} | {pr['headRefName']} | "
            f"{pr['title']}\n  {pr['url']}"
        )

    return prs


def sync_branch(branch, base_branch):
    """Fetch and update a local branch from origin."""
    git("fetch", "--prune", "origin")

    remote = git(
        "branch", "-r", "--list", f"origin/{branch}"
    ).stdout.strip()

    local = git(
        "branch", "--list", branch
    ).stdout.strip()

    if not local:
        if not remote:
            raise RuntimeError(
                f"Branch '{branch}' does not exist locally or remotely.\n"
                "If its PR was merged and GitHub deleted the source branch, "
                f"run the merged code from '{base_branch}' instead."
            )

        git(
            "switch", "--track", "-c", branch, f"origin/{branch}"
        )
    else:
        git("switch", branch)

    if remote:
        git("pull", "--ff-only", "origin", branch)
    elif branch == base_branch:
        raise RuntimeError(
            f"Could not find origin/{base_branch}. Check your remote."
        )
    else:
        print(
            f"Warning: origin/{branch} does not exist. "
            "The local branch was not updated."
        )


def run_ui_tests(issue_key=None):
    """Run generated Selenium tests with pytest."""
    tests_dir = REPO_DIR / "generated_tests"

    if not tests_dir.exists():
        raise RuntimeError(f"Generated tests directory not found: {tests_dir}")

    if issue_key:
        target = tests_dir / issue_key / "test_ui.py"
        if not target.exists():
            raise RuntimeError(f"UI test file not found: {target}")
        targets = [str(target)]
    else:
        targets = [
            str(path)
            for path in sorted(tests_dir.glob("*/test_ui.py"))
        ]

    if not targets:
        print("No generated Selenium test files were found.")
        return 0

    print("\nRunning Selenium tests:")
    for target in targets:
        print(" -", target)

    result = run_command(
        [
            sys.executable,
            "-m", "pytest",
            "-v",
            "--tb=short",
            *targets,
        ],
        check=False,
    )

    return result.returncode


def main():
    parser = argparse.ArgumentParser(
        description="Sync merged Jira test automation and run UI tests."
    )
    parser.add_argument(
        "--branch",
        default=DEFAULT_BASE_BRANCH,
        help="Branch to run locally (default: main).",
    )
    parser.add_argument(
        "--issue",
        help="Run only one Jira issue, e.g. SCRUM-2.",
    )
    parser.add_argument(
        "--list-only",
        action="store_true",
        help="List merged PRs without switching branches or running tests.",
    )
    args = parser.parse_args()

    print("Repository:", REPO_DIR)

    run_command(["gh", "auth", "status"])
    show_merged_prs(DEFAULT_BASE_BRANCH)

    if args.list_only:
        return

    ensure_clean_worktree()

    # A merged PR's changes are available on the base branch.
    sync_branch(args.branch, DEFAULT_BASE_BRANCH)

    print(f"\nRunning tests on branch: {args.branch}")

    exit_code = run_ui_tests(args.issue)

    if exit_code == 0:
        print("\nUI test run completed successfully.")
    else:
        print(f"\nUI tests failed. Exit code: {exit_code}")

    raise SystemExit(exit_code)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, json.JSONDecodeError) as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
