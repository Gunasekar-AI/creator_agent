
import re
import subprocess
from pathlib import Path


def run_git(*args, cwd):
    """Run a Git command and return its output."""
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Git command failed: git {' '.join(args)}\n"
            f"{result.stderr.strip()}"
        )

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

    # Make the branch name safe for Git.
    name = name.lower()
    name = re.sub(r"[^a-z0-9._/-]+", "-", name)
    name = re.sub(r"-+", "-", name)
    name = name.strip("-./")

    if not name:
        raise ValueError("Could not create a valid branch name")

    return name


def publish_generated_tests(
    issue_key,
    labels,
    output_dir,
    repo_dir=None,
    base_branch="main",
):
    """
    Create a Jira branch, commit generated tests, and push it.
    PR creation is handled separately by the repository provider.
    """
    repo = Path(repo_dir or Path.cwd()).resolve()
    output = Path(output_dir).resolve()

    if not (repo / ".git").exists():
        raise RuntimeError(f"Not a Git repository: {repo}")

    if not output.exists() or not any(output.iterdir()):
        raise RuntimeError(f"No generated files found in {output}")

    # Ensure output_dir belongs to this repository.
    try:
        output.relative_to(repo)
    except ValueError:
        raise RuntimeError(
            "Generated output directory must be inside the Git repository"
        )

    branch = make_branch_name(issue_key, labels)

    # Avoid switching branches with uncommitted user changes.
    status = run_git("status", "--porcelain", cwd=repo)
    if status:
        raise RuntimeError(
            "Git working tree is not clean. Commit or stash existing "
            "changes before running the publishing workflow."
        )

    # Verify the configured base branch exists on the remote.
    run_git("fetch", "origin", base_branch, cwd=repo)

    # Avoid silently overwriting an existing Jira branch.
    local_branches = run_git(
        "branch", "--list", branch, cwd=repo
    )
    remote_branches = run_git(
        "ls-remote", "--heads", "origin", f"refs/heads/{branch}",
        cwd=repo,
    )

    if local_branches or remote_branches:
        raise RuntimeError(
            f"Branch '{branch}' already exists locally or remotely. "
            "Use a new branch or handle the existing branch explicitly."
        )

    run_git("switch", "-c", branch, f"origin/{base_branch}", cwd=repo)

    # Stage only this Jira ticket's generated test files.
    relative_output = output.relative_to(repo).as_posix()
    run_git("add", "--", relative_output, cwd=repo)

    staged = run_git("diff", "--cached", "--name-only", cwd=repo)
    if not staged:
        raise RuntimeError("No generated changes to commit")

    run_git(
        "commit",
        "-m",
        f"test: generate automation for {issue_key}",
        cwd=repo,
    )

    run_git("push", "-u", "origin", branch, cwd=repo)

    print(f"Branch pushed: {branch}")
    print(f"Base branch: {base_branch}")
    print(f"Committed files:\n{staged}")

    return {
        "branch": branch,
        "base_branch": base_branch,
        "files": staged.splitlines(),
    }
