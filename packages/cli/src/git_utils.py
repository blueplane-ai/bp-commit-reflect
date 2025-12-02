"""
Git utility functions for extracting commit metadata.

This module provides functions for interacting with git repositories
to extract commit information needed for reflection context.
"""

import subprocess
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from packages.shared.types.reflection import CommitContext


class GitError(Exception):
    """Exception raised for git-related errors."""
    pass


def run_git_command(args: List[str], cwd: Optional[Path] = None) -> str:
    """
    Run a git command and return output.

    Args:
        args: Git command arguments (without 'git' prefix)
        cwd: Working directory (defaults to current directory)

    Returns:
        Command output as string

    Raises:
        GitError: If git command fails
    """
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise GitError(f"Git command failed: {e.stderr}") from e
    except FileNotFoundError:
        raise GitError("Git executable not found. Please ensure git is installed.") from None


def is_git_repository(path: Optional[Path] = None) -> bool:
    """
    Check if the current directory is a git repository.

    Args:
        path: Path to check (defaults to current directory)

    Returns:
        True if it's a git repository
    """
    try:
        run_git_command(["rev-parse", "--git-dir"], cwd=path)
        return True
    except GitError:
        return False


def get_current_branch(cwd: Optional[Path] = None) -> str:
    """
    Get the name of the current git branch.

    Args:
        cwd: Working directory (defaults to current directory)

    Returns:
        Branch name

    Raises:
        GitError: If not in a git repository or detached HEAD
    """
    try:
        return run_git_command(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)
    except GitError as e:
        # Check if it's a detached HEAD
        try:
            commit_hash = run_git_command(["rev-parse", "HEAD"], cwd=cwd)
            return f"detached-{commit_hash[:8]}"
        except GitError:
            raise e


def get_repository_root(cwd: Optional[Path] = None) -> Path:
    """
    Get the root directory of the git repository.

    Args:
        cwd: Working directory (defaults to current directory)

    Returns:
        Path to repository root

    Raises:
        GitError: If not in a git repository
    """
    output = run_git_command(["rev-parse", "--show-toplevel"], cwd=cwd)
    return Path(output)


def get_commit_hash(ref: str = "HEAD", cwd: Optional[Path] = None) -> str:
    """
    Get the full commit hash for a reference.

    Args:
        ref: Git reference (default: HEAD)
        cwd: Working directory (defaults to current directory)

    Returns:
        Full commit hash

    Raises:
        GitError: If reference doesn't exist
    """
    return run_git_command(["rev-parse", ref], cwd=cwd)


def get_short_commit_hash(ref: str = "HEAD", cwd: Optional[Path] = None) -> str:
    """
    Get the short commit hash for a reference.

    Args:
        ref: Git reference (default: HEAD)
        cwd: Working directory (defaults to current directory)

    Returns:
        Short commit hash (7 characters)

    Raises:
        GitError: If reference doesn't exist
    """
    return run_git_command(["rev-parse", "--short", ref], cwd=cwd)


def get_commit_message(commit_hash: str, cwd: Optional[Path] = None) -> str:
    """
    Get the commit message for a commit.

    Args:
        commit_hash: Commit hash or reference
        cwd: Working directory (defaults to current directory)

    Returns:
        Commit message

    Raises:
        GitError: If commit doesn't exist
    """
    return run_git_command(["log", "-1", "--format=%B", commit_hash], cwd=cwd)


def get_commit_author(commit_hash: str, cwd: Optional[Path] = None) -> Tuple[str, str]:
    """
    Get the author name and email for a commit.

    Args:
        commit_hash: Commit hash or reference
        cwd: Working directory (defaults to current directory)

    Returns:
        Tuple of (author_name, author_email)

    Raises:
        GitError: If commit doesn't exist
    """
    name = run_git_command(["log", "-1", "--format=%an", commit_hash], cwd=cwd)
    email = run_git_command(["log", "-1", "--format=%ae", commit_hash], cwd=cwd)
    return name, email


def get_commit_timestamp(commit_hash: str, cwd: Optional[Path] = None) -> datetime:
    """
    Get the timestamp of a commit.

    Args:
        commit_hash: Commit hash or reference
        cwd: Working directory (defaults to current directory)

    Returns:
        Commit timestamp as datetime

    Raises:
        GitError: If commit doesn't exist
    """
    # Get timestamp in ISO 8601 format
    timestamp_str = run_git_command(
        ["log", "-1", "--format=%aI", commit_hash],
        cwd=cwd
    )
    return datetime.fromisoformat(timestamp_str)


def get_changed_files(commit_hash: str, cwd: Optional[Path] = None) -> List[str]:
    """
    Get list of files changed in a commit.

    Args:
        commit_hash: Commit hash or reference
        cwd: Working directory (defaults to current directory)

    Returns:
        List of file paths

    Raises:
        GitError: If commit doesn't exist
    """
    output = run_git_command(
        ["diff-tree", "--no-commit-id", "--name-only", "-r", commit_hash],
        cwd=cwd
    )
    if not output:
        return []
    return output.split("\n")


def get_commit_stats(commit_hash: str, cwd: Optional[Path] = None) -> Dict[str, int]:
    """
    Get statistics for a commit (insertions, deletions).

    Args:
        commit_hash: Commit hash or reference
        cwd: Working directory (defaults to current directory)

    Returns:
        Dictionary with 'insertions', 'deletions', 'files_changed'

    Raises:
        GitError: If commit doesn't exist
    """
    output = run_git_command(
        ["show", "--shortstat", "--format=", commit_hash],
        cwd=cwd
    )

    stats = {
        "insertions": 0,
        "deletions": 0,
        "files_changed": 0,
    }

    # Parse output like: " 3 files changed, 150 insertions(+), 20 deletions(-)"
    if output:
        parts = output.strip().split(", ")
        for part in parts:
            if "file" in part:
                match = re.search(r'(\d+)', part)
                if match:
                    stats["files_changed"] = int(match.group(1))
            elif "insertion" in part:
                match = re.search(r'(\d+)', part)
                if match:
                    stats["insertions"] = int(match.group(1))
            elif "deletion" in part:
                match = re.search(r'(\d+)', part)
                if match:
                    stats["deletions"] = int(match.group(1))

    return stats


def get_commit_context(
    commit_hash: str = "HEAD",
    project: Optional[str] = None,
    branch: Optional[str] = None,
    cwd: Optional[Path] = None,
) -> CommitContext:
    """
    Get complete context for a commit.

    Args:
        commit_hash: Commit hash or reference (default: HEAD)
        project: Project name (inferred from repo if not provided)
        branch: Branch name (auto-detected if not provided)
        cwd: Working directory (defaults to current directory)

    Returns:
        CommitContext object with all commit metadata

    Raises:
        GitError: If not in a git repository or commit doesn't exist
    """
    # Ensure we're in a git repository
    if not is_git_repository(cwd):
        raise GitError("Not in a git repository")

    # Get full commit hash
    full_hash = get_commit_hash(commit_hash, cwd)

    # Get commit details
    message = get_commit_message(full_hash, cwd)
    author_name, author_email = get_commit_author(full_hash, cwd)
    timestamp = get_commit_timestamp(full_hash, cwd)
    files = get_changed_files(full_hash, cwd)
    stats = get_commit_stats(full_hash, cwd)

    # Get branch if not provided
    if branch is None:
        try:
            branch = get_current_branch(cwd)
        except GitError:
            branch = "unknown"

    # Get project name if not provided
    if project is None:
        try:
            repo_root = get_repository_root(cwd)
            project = repo_root.name
        except GitError:
            project = "unknown"

    # Create CommitContext
    return CommitContext(
        commit_hash=full_hash,
        commit_message=message,
        author_name=author_name,
        author_email=author_email,
        timestamp=timestamp,
        branch=branch,
        changed_files=files,
        files_changed=len(files),
        insertions=stats["insertions"],
        deletions=stats["deletions"],
    )


def get_commits_in_range(
    from_ref: str,
    to_ref: str = "HEAD",
    cwd: Optional[Path] = None,
) -> List[str]:
    """
    Get list of commit hashes in a range.

    Args:
        from_ref: Starting reference (exclusive)
        to_ref: Ending reference (inclusive, default: HEAD)
        cwd: Working directory (defaults to current directory)

    Returns:
        List of commit hashes

    Raises:
        GitError: If references don't exist
    """
    output = run_git_command(
        ["rev-list", f"{from_ref}..{to_ref}"],
        cwd=cwd
    )
    if not output:
        return []
    return output.split("\n")


def get_recent_commits(
    count: int = 10,
    cwd: Optional[Path] = None,
) -> List[str]:
    """
    Get list of recent commit hashes.

    Args:
        count: Number of commits to retrieve
        cwd: Working directory (defaults to current directory)

    Returns:
        List of commit hashes (most recent first)

    Raises:
        GitError: If not in a git repository
    """
    output = run_git_command(
        ["log", f"-{count}", "--format=%H"],
        cwd=cwd
    )
    if not output:
        return []
    return output.split("\n")
