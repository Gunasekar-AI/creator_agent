
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


def run_command(args, cwd, check=True):
    """Run a command and return its stdout."""
    result = subprocess.run(
        args,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )

    if check and result.returncode != 0:
        raise RuntimeError(
            f"Command failed: {' '.join(map(str, args))}\n"
            f"{result.stderr.strip() or result.stdout.strip()}"
        )

    return result


def run_git(*args, cwd):
    """Run a Git command and return its output."""
    return run_command(["git", *args], cwd=cwd).stdout.strip()


def make_branch_name(issue_key, labels):
    """Build a safe branch name from the Jira key and first label."""
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
    """Verify that GitHub CLI is installed and authenticated."""
    if not shutil.which("gh"):
        raise RuntimeError(
            "GitHub CLI (gh) is not installed or not on PATH. "
            "Install it and run 'gh auth login'."
        )

    run_command(["gh", "auth", "status"], cwd=repo)


def create_or_reuse_pr(repo, branch, base_branch, issue_key, summary):
    """Reuse an open PR for this branch, or create one."""
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
        summary.strip() if isinstance(summary, str) and summary.strip()
        else "Generated test automation"
    )
    title = f"{issue_key}: {title_summary}"

    body = (
        f"Automated test generation for Jira issue {issue_key}.\n\n"
        "Please review the generated UI/API tests and replace any "
        "TODO placeholders with the application's actual configuration."
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


def get_changed_paths(repo):
    """Return paths changed in the working tree or index."""
    result = run_git(
        "status", "--porcelain", "--untracked-files=all", cwd=repo
    )

    paths = []

    for line in result.splitlines():
        if len(line) < 4:
            continue

        # Git porcelain status may include rename records.
        path_text = line[3:].strip()

        if " -> " in path_text:
            path_text = path_text.split(" -> ", 1)[1]

        # Porcelain output quotes unusual filenames. This project uses
        # ordinary generated filenames, so normal paths are sufficient.
        paths.append(path_text.replace("\\", "/"))

    return paths


def path_is_inside(path, directory):
    """Check whether a changed path is the directory or one of its files."""
    return path == directory or path.startswith(directory.rstrip("/") + "/")


def publish_generated_tests(
    issue_key,
    labels,
    output_dir,
    repo_dir=None,
    base_branch="main",
    summary="",
):
    """
    Publish generated test files to a Jira-specific branch.

    Generated files inside output_dir are snapshotted before branch changes.
    Only that generated directory may contain working-tree changes. Changes
    elsewhere in the repository are preserved and cause publication to stop.
    """
    repo = Path(repo_dir or Path.cwd()).resolve()
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

    branch = make_branch_name(issue_key, labels)

    # Verify GitHub CLI before modifying the working tree.
    ensure_github_cli(repo)

    with tempfile.TemporaryDirectory(prefix="jira-generated-") as temp_dir:
        snapshot = Path(temp_dir) / "generated_output"
        shutil.copytree(output, snapshot)

        # Allow changes in this generated directory only. Its contents
        # are backed up above, so they can safely be replaced after switching.
        changed_paths = get_changed_paths(repo)
        unrelated = [
            path for path in changed_paths
            if not path_is_inside(path, relative_output)
        ]

        if unrelated:
            raise RuntimeError(
                "There are unrelated Git changes. Commit or safely stash "
                "them before publishing:\n"
                + "\n".join(unrelated)
            )

        # Fetch the base branch before selecting or creating the Jira branch.
        run_git("fetch", "origin", base_branch, cwd=repo)

        current_branch = run_git(
            "branch", "--show-current", cwd=repo
        )

        local_branch = run_git(
            "branch", "--list", branch, cwd=repo
        )

        remote_branch = run_git(
            "ls-remote", "--heads", "origin",
            f"refs/heads/{branch}", cwd=repo
        )

        # Clear only the generated output from the index and working tree.
        # The complete latest output is safe in the temporary snapshot.
        run_git(
            "restore",
            "--source=HEAD",
            "--staged",
            "--worktree",
            "--",
            relative_output,
            cwd=repo,
        )
        run_git("clean", "-fd", "--", relative_output, cwd=repo)

        # Switch to an existing branch or create it from the base branch.
        if current_branch == branch:
            pass
        elif local_branch:
            run_git("switch", branch, cwd=repo)
        elif remote_branch:
            run_git(
                "switch", "--track", "-c", branch,
                f"origin/{branch}", cwd=repo
            )
        else:
            run_git(
                "switch", "-c", branch,
                f"origin/{base_branch}", cwd=repo
            )

        # Incorporate remote changes before applying new generated output.
        remote_branch = run_git(
            "ls-remote", "--heads", "origin",
            f"refs/heads/{branch}", cwd=repo
        )

        if remote_branch:
            run_git("pull", "--rebase", "origin", branch, cwd=repo)

        # Restore the generated snapshot on the Jira branch.
        if output.exists():
            shutil.rmtree(output)

        shutil.copytree(snapshot, output)

        # Stage only this ticket's generated files.
        run_git("add", "--", relative_output, cwd=repo)

        staged = run_git(
            "diff", "--cached", "--name-only", cwd=repo
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

        # Push the Jira-specific branch.
        run_git("push", "-u", "origin", branch, cwd=repo)

        # Create or reuse its pull request.
        pr_url = create_or_reuse_pr(
            repo=repo,
            branch=branch,
            base_branch=base_branch,
            issue_key=issue_key,
            summary=summary,
        )

        print(f"Branch: {branch}")
        print(f"Base branch: {base_branch}")
        print(f"Changed files:\n{staged or '(none)'}")
        print(f"Pull request: {pr_url}")

        return {
            "branch": branch,
            "base_branch": base_branch,
            "files": staged.splitlines() if staged else [],
            "pr_url": pr_url,
        }
