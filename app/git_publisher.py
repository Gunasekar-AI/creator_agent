
import json
import re
import shutil
import subprocess
from pathlib import Path


def run_command(args, cwd, check=True):
    """Run a command and return its completed process."""
    result = subprocess.run(
        [str(arg) for arg in args],
        cwd=cwd,
        capture_output=True,
        text=True,
        errors="replace",
        check=False,
    )

    if check and result.returncode != 0:
        raise RuntimeError(
            f"Command failed: {' '.join(map(str, args))}\n"
            f"{result.stderr.strip() or result.stdout.strip()}"
        )

    return result


def run_git(*args, cwd):
    """Run Git and return stdout."""
    return run_command(["git", *args], cwd=cwd).stdout.rstrip("\r\n")


def make_branch_name(issue_key, labels):
    """Build a safe Jira-specific branch name."""
    name = str(issue_key)

    if isinstance(labels, str):
        labels = [labels]

    if labels:
        label = str(labels[0]).strip()
        if label:
            name = f"{name}-{label}"

    name = name.lower()
    name = re.sub(r"[^a-z0-9._/-]+", "-", name)
    name = re.sub(r"-+", "-", name)
    name = name.strip("-./")

    if not name:
        raise ValueError("Could not create a valid Git branch name.")

    return name


def ensure_github_cli(repo):
    """Verify GitHub CLI is installed and authenticated."""
    if not shutil.which("gh"):
        raise RuntimeError("GitHub CLI (gh) is not installed or on PATH.")

    run_command(["gh", "auth", "status"], cwd=repo)


def get_changed_paths(repo):
    """Return paths changed in the working tree or index."""
    output = run_command(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=repo,
    ).stdout.rstrip("\r\n")

    paths = []

    for line in output.splitlines():
        if len(line) < 4:
            continue

        path = line[3:].strip()

        if " -> " in path:
            path = path.split(" -> ", 1)[1]

        paths.append(path.replace("\\", "/"))

    return paths


def path_is_inside(path, directory):
    """Check whether a path is inside a directory."""
    path = path.replace("\\", "/").strip("/").lower()
    directory = directory.replace("\\", "/").strip("/").lower()

    return path == directory or path.startswith(directory + "/")


def get_repo_and_output(repo_dir, output_dir):
    """Resolve and validate repository and generated output paths."""
    repo = Path(repo_dir).resolve()
    output = Path(output_dir).resolve()

    if not (repo / ".git").exists():
        raise RuntimeError(f"Not a Git repository: {repo}")

    if not output.is_dir() or not any(output.iterdir()):
        raise RuntimeError(f"No generated files found in {output}")

    try:
        relative_output = output.relative_to(repo).as_posix()
    except ValueError as exc:
        raise RuntimeError(
            "Generated output directory must be inside the repository."
        ) from exc

    if relative_output in ("", "."):
        raise RuntimeError("Refusing to publish the repository root.")

    return repo, output, relative_output


def prepare_generated_tests(
    issue_key,
    labels,
    output_dir,
    repo_dir=None,
    base_branch="main",
):
    """
    Prepare a Jira branch and commit generated tests locally.

    This function DOES NOT push or create a pull request.
    """
    repo_dir = repo_dir or Path(__file__).resolve().parent.parent

    repo, output, relative_output = get_repo_and_output(
        repo_dir, output_dir
    )

    branch = make_branch_name(issue_key, labels)

    # Preserve generated output while switching branches.
    import tempfile

    with tempfile.TemporaryDirectory(prefix="jira-generated-") as temp:
        snapshot = Path(temp) / "generated_output"
        shutil.copytree(output, snapshot)

        # Do not disturb unrelated working-tree changes.
        changed_paths = get_changed_paths(repo)

        unrelated = [
            path for path in changed_paths
            if not path_is_inside(path, relative_output)
        ]

        if unrelated:
            raise RuntimeError(
                "Unrelated Git changes detected. "
                "Commit or safely stash them first:\n"
                + "\n".join(f"  - {path}" for path in unrelated)
            )

        # Fetch the latest base branch.
        run_git("fetch", "origin", base_branch, cwd=repo)

        current_branch = run_git(
            "branch", "--show-current", cwd=repo
        )

        local_branch = run_git(
            "branch", "--list", branch, cwd=repo
        )

        remote_branch = run_git(
            "ls-remote", "--heads", "origin",
            f"refs/heads/{branch}",
            cwd=repo,
        )

        # Remove only generated-directory changes before switching.
        run_git(
            "restore",
            "--source=HEAD",
            "--staged",
            "--worktree",
            "--",
            relative_output,
            cwd=repo,
        )

        run_git(
            "clean", "-fd", "--", relative_output, cwd=repo
        )

        # Select the Jira branch.
        if current_branch == branch:
            pass
        elif local_branch:
            run_git("switch", branch, cwd=repo)
        elif remote_branch:
            run_git(
                "switch",
                "--track",
                "-c",
                branch,
                f"origin/{branch}",
                cwd=repo,
            )
        else:
            run_git(
                "switch",
                "-c",
                branch,
                f"origin/{base_branch}",
                cwd=repo,
            )

        # Bring an existing remote Jira branch up to date.
        remote_branch = run_git(
            "ls-remote", "--heads", "origin",
            f"refs/heads/{branch}",
            cwd=repo,
        )

        if remote_branch:
            run_git(
                "pull", "--rebase", "origin", branch, cwd=repo
            )

        # Restore the newly generated files.
        if output.exists():
            shutil.rmtree(output)

        shutil.copytree(snapshot, output)

        # Stage only this Jira ticket's generated files.
        run_git("add", "--", relative_output, cwd=repo)

        staged = run_git(
            "diff", "--cached", "--name-only", cwd=repo
        )

        # Verify that only the intended directory is staged.
        staged_paths = staged.splitlines()

        unexpected = [
            path for path in staged_paths
            if not path_is_inside(path, relative_output)
        ]

        if unexpected:
            raise RuntimeError(
                "Unexpected files staged for commit:\n"
                + "\n".join(unexpected)
            )

        if staged:
            run_git(
                "commit",
                "-m",
                f"test: generate automation for {issue_key}",
                cwd=repo,
            )
        else:
            print("No generated-file changes to commit.")

        commit = run_git("rev-parse", "HEAD", cwd=repo)

        # Require a clean working tree before testing.
        remaining = get_changed_paths(repo)

        if remaining:
            raise RuntimeError(
                "Working tree is not clean after preparation:\n"
                + "\n".join(remaining)
            )

        return {
            "issue_key": issue_key,
            "branch": branch,
            "base_branch": base_branch,
            "commit": commit,
            "files": staged_paths,
            "pushed": False,
        }


def create_or_reuse_pr(
    repo,
    branch,
    base_branch,
    issue_key,
    summary,
):
    """Reuse an open PR or create a new one."""
    existing = run_command(
        [
            "gh", "pr", "list",
            "--head", branch,
            "--base", base_branch,
            "--state", "open",
            "--json", "url",
        ],
        cwd=repo,
    )

    prs = json.loads(existing.stdout or "[]")

    if prs:
        return prs[0]["url"]

    title_summary = (
        summary.strip()
        if isinstance(summary, str) and summary.strip()
        else "Generated test automation"
    )

    title = f"{issue_key}: {title_summary}"

    body = (
        f"Automated test changes for Jira issue {issue_key}.\n\n"
        "UI and API tests were executed locally before publication. "
        "See the automated test execution comment for results and evidence."
    )

    created = run_command(
        [
            "gh", "pr", "create",
            "--base", base_branch,
            "--head", branch,
            "--title", title,
            "--body", body,
        ],
        cwd=repo,
    )

    return created.stdout.strip()


def add_test_results_comment(
    repo,
    pr_url,
    issue_key,
    test_summary,
    tested_commit,
):
    """Add test results and execution commands to a pull request."""
    suites = test_summary.get("suites", [])

    lines = [
        "## Automated Test Execution Results",
        "",
        f"**Jira:** {issue_key}",
        f"**Tested commit:** `{tested_commit}`",
        f"**Overall status:** {test_summary.get('overall_status', 'UNKNOWN')}",
        "",
        "| Test suite | Result | Exit code |",
        "|---|---|---:|",
    ]

    for suite in suites:
        lines.append(
            f"| {suite.get('suite', 'Unknown')} "
            f"| {suite.get('status', 'UNKNOWN')} "
            f"| {suite.get('exit_code', 'N/A')} |"
        )

    lines.extend([
        "",
        "### Commands executed",
        "",
        "```powershell",
        f"python -m app.local_test_runner {issue_key}",
        "```",
        "",
        "### Evidence",
        "",
        f"Evidence folder: `{test_summary.get('evidence_dir', 'Not provided')}`",
        f"Summary: `{test_summary.get('summary_path', 'Not provided')}`",
    ])

    for suite in suites:
        if suite.get("log"):
            lines.append(
                f"- {suite.get('suite', 'Test')} log: `{suite['log']}`"
            )

        if suite.get("html_report"):
            lines.append(
                f"- Karate HTML report: `{suite['html_report']}`"
            )

    body = "\n".join(lines)

    run_command(
        ["gh", "pr", "comment", pr_url, "--body", body],
        cwd=repo,
    )


def publish_tested_branch(
    issue_key,
    prepared,
    test_summary,
    repo_dir=None,
    summary="",
):
    """
    Publish a previously tested commit.

    Refuses publication unless all requested test suites passed
    and the current commit still matches the tested commit.
    """
    repo = Path(
        repo_dir or Path(__file__).resolve().parent.parent
    ).resolve()

    if test_summary.get("overall_status") != "PASS":
        raise RuntimeError(
            "Tests did not pass. Refusing to publish."
        )

    suites = test_summary.get("suites", [])

    if not suites or any(
        suite.get("status") != "PASS" for suite in suites
    ):
        raise RuntimeError(
            "One or more test suites did not pass. Refusing to publish."
        )

    branch = prepared["branch"]
    tested_commit = test_summary.get("git_commit")
    prepared_commit = prepared.get("commit")

    if not tested_commit or tested_commit != prepared_commit:
        raise RuntimeError(
            "Tested commit does not match the prepared commit. "
            "Refusing to publish."
        )

    current_branch = run_git(
        "branch", "--show-current", cwd=repo
    )

    current_commit = run_git(
        "rev-parse", "HEAD", cwd=repo
    )

    if current_branch != branch:
        raise RuntimeError(
            f"Expected branch {branch}, found {current_branch}."
        )

    if current_commit != tested_commit:
        raise RuntimeError(
            "Git commit changed after testing. Tests must be rerun."
        )

    if get_changed_paths(repo):
        raise RuntimeError(
            "Working tree changed after testing. "
            "Tests must be rerun before publication."
        )

    ensure_github_cli(repo)

    base_branch = prepared["base_branch"]

    # Push the exact tested commit.
    run_git(
        "push", "-u", "origin", branch, cwd=repo
    )

    pr_url = create_or_reuse_pr(
        repo=repo,
        branch=branch,
        base_branch=base_branch,
        issue_key=issue_key,
        summary=summary,
    )

    add_test_results_comment(
        repo=repo,
        pr_url=pr_url,
        issue_key=issue_key,
        test_summary=test_summary,
        tested_commit=tested_commit,
    )

    return {
        **prepared,
        "pushed": True,
        "pr_url": pr_url,
        "tested_commit": tested_commit,
        "test_status": "PASS",
    }


# Compatibility guard: old callers must not bypass the test gate.
def publish_generated_tests(*args, **kwargs):
    raise RuntimeError(
        "Direct publishing is disabled. Use prepare_generated_tests(), "
        "run the tests, then call publish_tested_branch()."
    )


def find_open_pr(repo, branch, base_branch):
    """Find an existing open PR for a Jira branch."""
    result = run_command(
        [
            "gh", "pr", "list",
            "--head", branch,
            "--base", base_branch,
            "--state", "open",
            "--json", "url",
        ],
        cwd=repo,
    )

    prs = json.loads(result.stdout or "[]")
    return prs[0]["url"] if prs else None


def add_test_failure_comment(
    repo,
    issue_key,
    branch,
    base_branch,
    test_summary,
):
    """Comment on an existing PR when tests fail, without publishing."""
    ensure_github_cli(repo)

    pr_url = find_open_pr(repo, branch, base_branch)

    if not pr_url:
        print(
            f"No existing PR found for {issue_key}. "
            "Failure evidence remains in test-results."
        )
        return None

    lines = [
        "## Automated Test Execution — FAILED",
        "",
        f"**Jira:** {issue_key}",
        f"**Tested commit:** `{test_summary.get('git_commit', 'unknown')}`",
        f"**Overall status:** {test_summary.get('overall_status', 'UNKNOWN')}",
        "",
        "| Suite | Status | Exit code |",
        "|---|---|---:|",
    ]

    for suite in test_summary.get("suites", []):
        lines.append(
            f"| {suite.get('suite', 'Unknown')} "
            f"| {suite.get('status', 'UNKNOWN')} "
            f"| {suite.get('exit_code', 'N/A')} |"
        )

    for suite in test_summary.get("suites", []):
        if suite.get("status") == "PASS":
            continue

        lines.extend([
            "",
            f"### {suite.get('suite', 'Test')} failure",
            f"Log: `{suite.get('log', 'Not available')}`",
            "",
            "```text",
            str(
                suite.get("failure_excerpt")
                or suite.get("message")
                or "No failure output captured."
            )[:6000],
            "```",
        ])

    lines.extend([
        "",
        f"Evidence: `{test_summary.get('evidence_dir', 'Not available')}`",
        "",
        "**Publication blocked: required tests did not pass.**",
    ])

    run_command(
        [
            "gh", "pr", "comment",
            pr_url,
            "--body",
            "\n".join(lines),
        ],
        cwd=repo,
    )

    return pr_url
