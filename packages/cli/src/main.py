"""Main CLI entry point with mode selection."""

import sys
import argparse
from typing import Optional


def create_parser() -> argparse.ArgumentParser:
    """
    Create argument parser for CLI.

    Returns:
        Configured ArgumentParser
    """
    parser = argparse.ArgumentParser(
        prog="commit-reflect",
        description="Capture reflections and AI synergy assessments at commit time"
    )

    # Mode selection
    parser.add_argument(
        "--mode",
        choices=["cli", "mcp-session"],
        default="cli",
        help="Execution mode: 'cli' for interactive terminal, 'mcp-session' for MCP protocol"
    )

    # Project and commit info
    parser.add_argument(
        "--project",
        required=True,
        help="Project name"
    )

    parser.add_argument(
        "--branch",
        help="Git branch name"
    )

    parser.add_argument(
        "--commit",
        help="Commit hash (single commit mode)"
    )

    parser.add_argument(
        "--commits",
        help="Comma-separated commit hashes (batch mode)"
    )

    # Configuration
    parser.add_argument(
        "--config",
        help="Path to configuration file"
    )

    parser.add_argument(
        "--storage",
        help="Storage backends to use (comma-separated: jsonl,database,git)"
    )

    parser.add_argument(
        "--jsonl-path",
        help="Path to JSONL storage file"
    )

    parser.add_argument(
        "--db-path",
        help="Path to SQLite database"
    )

    # Session management
    parser.add_argument(
        "--session-id",
        help="Session ID for MCP mode"
    )

    parser.add_argument(
        "--recover",
        action="store_true",
        help="Attempt to recover incomplete session"
    )

    return parser


def main(argv: Optional[list] = None) -> int:
    """
    Main entry point for commit-reflect CLI.

    Args:
        argv: Command-line arguments (defaults to sys.argv)

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    parser = create_parser()
    args = parser.parse_args(argv)

    # Route to appropriate mode
    if args.mode == "mcp-session":
        from .mcp_mode import run_mcp_mode
        return run_mcp_mode()
    else:
        # Interactive CLI mode
        from .cli_mode import run_interactive_mode
        return run_interactive_mode(args)


if __name__ == "__main__":
    sys.exit(main())
