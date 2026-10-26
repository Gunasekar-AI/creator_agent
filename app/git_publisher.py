
import json
import os
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
    result = run_command(["git", *args], cwd=cwd)
    return result.stdout.strip()


def make_branch_name(issue_key, labels):
    """Build a safe branch name from the Jira key and first label."""
    name = issue_key

    if isinstance(labels, str):
        labels = [labels]

    if labels:
        label = str(labels[0]).strip()
        if label:
            name = f"{issue_key}-{label}"

    name = name.lower()
    name = re.sub(r"[^a-z0-9._/-]+", "-", name)
    name = re.sub(r"-+", "-", name)
    name = name.strip("-./")

    if not name:
        raise ValueError("Could not create a valid Git branch name")

    return name


def ensure_github_cli(repo):
    """Verify that GitHub CLI is installed and authenticated."""
    if not shutil.which("gh"):
        raise RuntimeError(
            "GitHub CLI (gh) is not installed or is not on PATH. "
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

    title_summary = summary.strip() if summary else "Generated test automation"
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


def publish_generated_tests(
    issue_key,
    labels,
    output_dir,
    repo_dir=None,
    base_branch="main",
    summary="",
):
    """
    Preserve generated files, switch to the Jira branch, commit and push
    the files, and create or reuse a GitHub pull request.

    Generated output is backed up outside the repository before changing
    branches. This avoids using 'git stash pop' on generated files.
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
            "Generated output directory must be inside the repository"
        ) from exc

    if relative_output in ("", "."):
        raise RuntimeError("Refusing to publish the repository root")

    branch = make_branch_name(issue_key, labels)

    # Check GitHub authentication before making repository changes.
    ensure_github_cli(repo)

    # Preserve the newest generated files outside the repository.
    with tempfile.TemporaryDirectory(prefix="jira-generated-") as temp_dir:
        snapshot = Path(temp_dir) / "generated_output"
        shutil.copytree(output, snapshot)

        # Allow changes only under this ticket's generated output directory.
        status = run_git(
            "status", "--porcelain", "--untracked-files=all", cwd=repo
        )
        unrelated = []

        for line in status.splitlines():
            changed_path = line[3:].strip().replace("\\", "/")

            # Rename records may contain "old -> new".
            if " -> " in changed_path:
                changed_path = changed_path.split(" -> ", 1)[1]

            if not (
                changed_path == relative_output
                or changed_path.startswith(relative_output + "/")
            ):
                unrelated.append(line)

        if unrelated:
            raise RuntimeError(
                "There are unrelated Git changes. Commit or safely stash "
                "them before publishing:\n" + "\n".join(unrelated)
            )

        # Reset only this generated directory. The latest files are safe
        # in the temporary snapshot, and unrelated files are not touched.
        run_git(
            "restore", "--source=HEAD", "--staged", "--worktree",
            "--", relative_output,
            cwd=repo,
        )
        run_git("clean", "-fd", "--", relative_output, cwd=repo)

        # Fetch the target branch and inspect local/remote Jira branches.
        run_git("fetch", "origin", base_branch, cwd=repo)

        local_branch = run_git(
            "branch", "--list", branch, cwd=repo
        )
        remote_branch = run_git(
            "ls-remote", "--heads", "origin", f"refs/heads/{branch}",
            cwd=repo,
        )

        current_branch = run_git(
            "branch", "--show-current", cwd=repo
        )

        if current_branch == branch:
            # Already on the intended Jira branch.
            pass
        elif local_branch:
            run_git("switch", branch, cwd=repo)
        elif remote_branch:
            run_git(
                "switch", "--track", "-c", branch,
                f"origin/{branch}", cwd=repo,
            )
        else:
            run_git(
                "switch", "-c", branch,
                f"origin/{base_branch}", cwd=repo,
            )

        # If the branch already exists remotely, incorporate its latest
        # commits before applying the new generated files.
        remote_branch = run_git(
            "ls-remote", "--heads", "origin", f"refs/heads/{branch}",
            cwd=repo,
        )
        if remote_branch:
            run_git("pull", "--rebase", "origin", branch, cwd=repo)

        # Replace this ticket's output directory with the saved snapshot.
        # Removing the old directory also removes obsolete generated files.
        if output.exists():
            shutil.rmtree(output)

        shutil.copytree(snapshot, output)

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

        # Push new commits; if there are no new commits, this still ensures
        # the branch is published when necessary.
        run_git("push", "-u", "origin", branch, cwd=repo)

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
