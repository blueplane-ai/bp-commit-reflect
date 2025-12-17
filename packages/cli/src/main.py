"""Main CLI entry point with mode selection."""

import argparse
import asyncio
import sys
from importlib.metadata import version, PackageNotFoundError
from pathlib import Path


def get_version() -> str:
    """Get package version from metadata or fallback."""
    try:
        return version("commit-reflect")
    except PackageNotFoundError:
        return "0.1.0"  # Fallback for development


def create_parser() -> argparse.ArgumentParser:
    """
    Create argument parser for CLI.

    Returns:
        Configured ArgumentParser
    """
    parser = argparse.ArgumentParser(
        prog="commit-reflect",
        description="Capture reflections and AI synergy assessments at commit time",
    )

    parser.add_argument(
        "--version", "-V", action="version", version=f"%(prog)s {get_version()}"
    )

    # Create subparsers for commands
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Install hook subcommand
    install_parser = subparsers.add_parser(
        "install-hook", help="Install git post-commit hook locally in a repository"
    )
    install_parser.add_argument(
        "--repo",
        type=Path,
        default=None,
        help="Path to git repository (defaults to current directory)",
    )
    install_parser.add_argument(
        "--force", action="store_true", help="Overwrite existing hook if present"
    )
    install_parser.add_argument(
        "--port", type=int, default=9123, help="Port for REPL server (default: 9123)"
    )

    # Uninstall hook subcommand
    uninstall_parser = subparsers.add_parser(
        "uninstall-hook", help="Remove git post-commit hook from a repository"
    )
    uninstall_parser.add_argument(
        "--repo",
        type=Path,
        default=None,
        help="Path to git repository (defaults to current directory)",
    )

    # Main arguments (for non-subcommand usage)
    # Mode selection
    parser.add_argument(
        "--mode",
        choices=["cli", "mcp-session", "repl"],
        default="cli",
        help="Execution mode: 'cli' for interactive terminal, 'mcp-session' for MCP protocol, 'repl' for persistent listener",
    )

    # Project and commit info
    parser.add_argument("--project", help="Project name (auto-detected if not provided)")

    parser.add_argument("--branch", help="Git branch name")

    parser.add_argument("--commit", help="Commit hash (single commit mode)")

    parser.add_argument("--commits", help="Comma-separated commit hashes (batch mode)")

    # Configuration
    parser.add_argument("--config", help="Path to configuration file")

    parser.add_argument(
        "--storage", help="Storage backends to use (comma-separated: jsonl,database,git)"
    )

    parser.add_argument("--jsonl-path", help="Path to JSONL storage file")

    parser.add_argument("--db-path", help="Path to SQLite database")

    # REPL mode specific
    parser.add_argument(
        "--port", type=int, default=9123, help="Port for REPL HTTP server (default: 9123)"
    )

    # Session management
    parser.add_argument("--session-id", help="Session ID for MCP mode")

    parser.add_argument(
        "--recover", action="store_true", help="Attempt to recover incomplete session"
    )

    return parser


def get_project_name() -> str:
    """
    Auto-detect project name from git repository.

    Returns:
        Project name or 'unknown'
    """
    try:
        from .git_utils import get_repository_root

        repo_root = get_repository_root()
        return repo_root.name
    except Exception:
        return Path.cwd().name


def main(argv: list | None = None) -> int:
    """
    Main entry point for commit-reflect CLI.

    Args:
        argv: Command-line arguments (defaults to sys.argv)

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    parser = create_parser()
    args = parser.parse_args(argv)

    # Handle subcommands
    if args.command == "install-hook":
        return handle_install_hook(args)
    elif args.command == "uninstall-hook":
        return handle_uninstall_hook(args)

    # Route to appropriate mode
    if args.mode == "repl":
        return handle_repl_mode(args)
    elif args.mode == "mcp-session":
        from .mcp_mode import run_mcp_mode

        return run_mcp_mode()
    else:
        # Interactive CLI mode - requires project
        if not args.project:
            args.project = get_project_name()

        from .cli_mode import run_interactive_mode

        return run_interactive_mode(args)


def handle_repl_mode(args: argparse.Namespace) -> int:
    """
    Handle REPL mode execution.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code
    """
    # Get project name if not provided
    project = args.project or get_project_name()

    from .repl import run_repl_mode

    # Run the async REPL
    return asyncio.run(
        run_repl_mode(
            project=project,
            port=args.port,
            config=None,  # TODO: Load from args.config if provided
            working_dir=Path.cwd(),
        )
    )


def handle_install_hook(args: argparse.Namespace) -> int:
    """
    Handle install-hook subcommand.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code
    """
    # Get repo path (default to current directory)
    repo_path = args.repo if args.repo else Path.cwd()

    try:
        # Import hook installer
        from cli.hooks.install import install_hook

        success = install_hook(
            repo_path=repo_path,
            force=args.force,
            port=args.port,
        )
        return 0 if success else 1
    except ImportError:
        # Fallback: inline implementation
        return install_hook_inline(repo_path, args.force, args.port)


def handle_uninstall_hook(args: argparse.Namespace) -> int:
    """
    Handle uninstall-hook subcommand.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code
    """
    # Get repo path (default to current directory)
    repo_path = args.repo if args.repo else Path.cwd()

    try:
        from cli.hooks.install import uninstall_hook

        success = uninstall_hook(repo_path=repo_path)
        return 0 if success else 1
    except ImportError:
        # Fallback: inline implementation
        return uninstall_hook_inline(repo_path)


def install_hook_inline(repo_path: Path, force: bool = False, port: int = 9123) -> int:
    """
    Install git hook (inline implementation).

    Args:
        repo_path: Path to git repository
        force: Overwrite existing hook
        port: Port for REPL server

    Returns:
        Exit code
    """
    import stat

    print(f"Installing hook in repository: {repo_path}")

    hook_script = f"""#!/bin/sh
#
# post-commit hook for commit-reflect REPL integration
# Sends commit notification to REPL server (fails silently if not running)
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

# Attempt to notify REPL server (fail silently)
curl -s --max-time "$TIMEOUT" \\
    -X POST "http://${{REPL_HOST}}:${{REPL_PORT}}/commit" \\
    -d "hash=${{COMMIT_HASH}}&project=${{PROJECT}}&branch=${{BRANCH}}&repo_path=${{REPO_ROOT}}" \\
    >/dev/null 2>&1 || true

# Always exit successfully (don't block commit)
exit 0
"""

    # Find .git/hooks directory
    hooks_dir = repo_path / ".git" / "hooks"
    if not hooks_dir.exists():
        # Try to create if .git exists
        git_dir = repo_path / ".git"
        if git_dir.exists():
            hooks_dir.mkdir(parents=True, exist_ok=True)
        else:
            print(f"Error: {repo_path} is not a git repository")
            return 1

    hook_path = hooks_dir / "post-commit"

    # Check if hook exists
    if hook_path.exists() and not force:
        content = hook_path.read_text()
        if "commit-reflect" in content:
            print(f"Hook already installed at {hook_path}")
            print("Use --force to reinstall")
            return 0
        else:
            print(f"Warning: Different hook exists at {hook_path}")
            print("Use --force to overwrite")
            return 1

    # Write hook
    hook_path.write_text(hook_script)

    # Make executable
    hook_path.chmod(hook_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    print(f"Installed post-commit hook at {hook_path}")
    print(f"Hook will notify REPL server on port {port}")
    return 0


def uninstall_hook_inline(repo_path: Path) -> int:
    """
    Uninstall git hook (inline implementation).

    Args:
        repo_path: Path to git repository

    Returns:
        Exit code
    """
    hook_path = repo_path / ".git" / "hooks" / "post-commit"

    if not hook_path.exists():
        print("No post-commit hook found")
        return 1

    # Check if it's our hook
    content = hook_path.read_text()
    if "commit-reflect" not in content:
        print("Warning: Hook does not appear to be from commit-reflect")
        print("Not removing to avoid breaking other integrations")
        return 1

    hook_path.unlink()
    print(f"Removed post-commit hook from {hook_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
