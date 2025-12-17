"""Git hook installation utility for commit-reflect REPL integration.

Installs hooks locally in a repository's .git/hooks/ directory.
Does NOT use global git hooks.
"""

import shutil
import stat
from pathlib import Path


def get_package_root() -> Path:
    """Get the root of the commit-reflect package."""
    # This file is at packages/cli/hooks/install.py
    # Package root is 3 levels up
    return Path(__file__).parent.parent.parent.parent


def get_hook_template_path() -> Path:
    """Get path to the hook template in .git-tools/hooks/."""
    return get_package_root() / ".git-tools" / "hooks" / "post-commit"


def get_hooks_dir(repo_path: Path | None = None) -> Path | None:
    """
    Get the .git/hooks directory for a repository.

    Args:
        repo_path: Path to repository root (defaults to current directory)

    Returns:
        Path to hooks directory, or None if not a git repository
    """
    if repo_path is None:
        repo_path = Path.cwd()
    else:
        repo_path = Path(repo_path).resolve()

    hooks_dir = repo_path / ".git" / "hooks"
    if hooks_dir.exists():
        return hooks_dir

    # Check if it's a git repo at all
    git_dir = repo_path / ".git"
    if git_dir.exists():
        # Create hooks dir if .git exists but hooks doesn't
        hooks_dir.mkdir(parents=True, exist_ok=True)
        return hooks_dir

    return None


def is_our_hook(hook_path: Path) -> bool:
    """
    Check if a hook file was installed by commit-reflect.

    Args:
        hook_path: Path to the hook file

    Returns:
        True if the hook contains our signature
    """
    if not hook_path.exists():
        return False

    try:
        content = hook_path.read_text()
        return "commit-reflect" in content
    except Exception:
        return False


def install_hook(
    repo_path: Path | None = None,
    force: bool = False,
    port: int = 9123,
) -> bool:
    """
    Install the post-commit hook locally in a git repository.

    Copies the hook from .git-tools/hooks/post-commit to the target
    repository's .git/hooks/post-commit.

    Args:
        repo_path: Path to repository root (defaults to current directory)
        force: Overwrite existing hook if present
        port: Default port for REPL server (embedded in hook)

    Returns:
        True if installed successfully
    """
    # Resolve repo path
    if repo_path is None:
        repo_path = Path.cwd()
    else:
        repo_path = Path(repo_path).resolve()

    print(f"Installing hook in repository: {repo_path}")

    # Get hooks directory
    hooks_dir = get_hooks_dir(repo_path)
    if hooks_dir is None:
        print(f"Error: {repo_path} is not a git repository")
        return False

    hook_path = hooks_dir / "post-commit"

    # Check for existing hook
    if hook_path.exists():
        if is_our_hook(hook_path):
            if not force:
                print(f"Hook already installed at {hook_path}")
                print("Use --force to reinstall")
                return True  # Already installed is success
        else:
            if not force:
                print(f"Warning: Different hook exists at {hook_path}")
                print("Use --force to overwrite (this will replace the existing hook)")
                return False

        # Backup existing hook if not ours
        if not is_our_hook(hook_path):
            backup_path = hook_path.with_suffix(".backup")
            print(f"Backing up existing hook to {backup_path}")
            shutil.copy2(hook_path, backup_path)

    # Get hook template
    template_path = get_hook_template_path()

    if template_path.exists():
        # Copy from template
        hook_content = template_path.read_text()
        # Replace default port if different from 9123
        if port != 9123:
            hook_content = hook_content.replace(
                "COMMIT_REFLECT_PORT:-9123", f"COMMIT_REFLECT_PORT:-{port}"
            )
    else:
        # Fallback: generate inline if template not found
        print(f"Warning: Template not found at {template_path}, using inline script")
        hook_content = generate_hook_script(port)

    # Write hook file
    hook_path.write_text(hook_content)

    # Make executable (rwxr-xr-x)
    hook_path.chmod(hook_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    print(f"Installed post-commit hook at {hook_path}")
    print(f"Hook will notify REPL server on port {port}")
    print()
    print("To start the REPL server, run:")
    print(f"  commit-reflect --mode repl --port {port}")

    return True


def generate_hook_script(port: int = 9123) -> str:
    """
    Generate hook script content (fallback if template not found).

    Args:
        port: Default port for REPL server

    Returns:
        Hook script content
    """
    return f"""#!/bin/sh
#
# post-commit hook for commit-reflect REPL integration
# Sends commit notification to REPL server (fails silently if not running)
#
# Installed by: commit-reflect install-hook
#

REPL_PORT="${{COMMIT_REFLECT_PORT:-{port}}}"
REPL_HOST="${{COMMIT_REFLECT_HOST:-127.0.0.1}}"
TIMEOUT=2

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
if [ -z "$REPO_ROOT" ]; then
    exit 0
fi

COMMIT_HASH=$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null)
PROJECT=$(basename "$REPO_ROOT")
BRANCH=$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")

if [ -z "$COMMIT_HASH" ]; then
    exit 0
fi

curl -s --max-time "$TIMEOUT" \\
    -X POST "http://${{REPL_HOST}}:${{REPL_PORT}}/commit" \\
    -d "hash=${{COMMIT_HASH}}&project=${{PROJECT}}&branch=${{BRANCH}}&repo_path=${{REPO_ROOT}}" \\
    >/dev/null 2>&1 || true

exit 0
"""


def uninstall_hook(repo_path: Path | None = None) -> bool:
    """
    Remove the post-commit hook from a git repository.

    Only removes hooks installed by commit-reflect.

    Args:
        repo_path: Path to repository root (defaults to current directory)

    Returns:
        True if uninstalled successfully
    """
    # Resolve repo path
    if repo_path is None:
        repo_path = Path.cwd()
    else:
        repo_path = Path(repo_path).resolve()

    hooks_dir = get_hooks_dir(repo_path)
    if hooks_dir is None:
        print(f"Error: {repo_path} is not a git repository")
        return False

    hook_path = hooks_dir / "post-commit"

    if not hook_path.exists():
        print("No post-commit hook found")
        return False

    # Safety check: only remove our hook
    if not is_our_hook(hook_path):
        print("Warning: Hook does not appear to be from commit-reflect")
        print("Not removing to avoid breaking other integrations")
        return False

    # Remove hook
    hook_path.unlink()
    print(f"Removed post-commit hook from {hook_path}")

    # Restore backup if exists
    backup_path = hook_path.with_suffix(".backup")
    if backup_path.exists():
        print(f"Restoring backup from {backup_path}")
        shutil.copy2(backup_path, hook_path)
        backup_path.unlink()

    return True


def is_hook_installed(repo_path: Path | None = None) -> bool:
    """
    Check if our hook is installed in a repository.

    Args:
        repo_path: Path to repository root (defaults to current directory)

    Returns:
        True if our hook is installed
    """
    if repo_path is None:
        repo_path = Path.cwd()
    else:
        repo_path = Path(repo_path).resolve()

    hooks_dir = get_hooks_dir(repo_path)
    if hooks_dir is None:
        return False

    hook_path = hooks_dir / "post-commit"
    return is_our_hook(hook_path)


def get_hook_port(repo_path: Path | None = None) -> int | None:
    """
    Get the configured port from an installed hook.

    Args:
        repo_path: Path to repository root (defaults to current directory)

    Returns:
        Port number, or None if not installed or can't determine
    """
    if repo_path is None:
        repo_path = Path.cwd()
    else:
        repo_path = Path(repo_path).resolve()

    hooks_dir = get_hooks_dir(repo_path)
    if hooks_dir is None:
        return None

    hook_path = hooks_dir / "post-commit"
    if not hook_path.exists():
        return None

    try:
        content = hook_path.read_text()
        # Look for default port in COMMIT_REFLECT_PORT:-XXXX pattern
        import re

        match = re.search(r"COMMIT_REFLECT_PORT:-(\d+)", content)
        if match:
            return int(match.group(1))
    except Exception:
        pass

    return 9123  # Default


# CLI interface for standalone usage
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Install/uninstall commit-reflect git hook (local to repository)"
    )

    # Common argument for all subcommands
    parser.add_argument(
        "--repo",
        type=Path,
        default=None,
        help="Path to git repository (defaults to current directory)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    install_parser = subparsers.add_parser("install", help="Install hook")
    install_parser.add_argument("--force", action="store_true", help="Overwrite existing hook")
    install_parser.add_argument("--port", type=int, default=9123, help="REPL server port")

    uninstall_parser = subparsers.add_parser("uninstall", help="Uninstall hook")

    status_parser = subparsers.add_parser("status", help="Check hook status")

    args = parser.parse_args()

    if args.command == "install":
        success = install_hook(repo_path=args.repo, force=args.force, port=args.port)
        exit(0 if success else 1)
    elif args.command == "uninstall":
        success = uninstall_hook(repo_path=args.repo)
        exit(0 if success else 1)
    elif args.command == "status":
        if is_hook_installed(repo_path=args.repo):
            port = get_hook_port(repo_path=args.repo)
            print(f"Hook installed (port: {port})")
            exit(0)
        else:
            print("Hook not installed")
            exit(1)
