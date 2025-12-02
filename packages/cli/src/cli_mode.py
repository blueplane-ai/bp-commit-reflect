"""
Interactive CLI mode for commit reflection.

This module implements the interactive terminal-based reflection flow.
"""

import sys
from pathlib import Path
from typing import Optional
from argparse import Namespace

from packages.shared.types.config import Config, StorageConfig
from packages.shared.types.question import create_default_question_set
from packages.shared.storage.factory import create_storage_from_config
from packages.cli.src.session import ReflectionSession
from packages.cli.src.git_utils import get_commit_context, GitError
from packages.cli.src.prompts import (
    display_welcome,
    display_error,
    display_validation_error,
    prompt_for_answer,
    display_summary,
    confirm_submission,
    display_completion_message,
)
from packages.cli.src.errors import ConfigurationError, StorageError
from packages.cli.src.progress import ProgressIndicator


def load_config(config_path: Optional[str], args: Namespace) -> Config:
    """
    Load configuration from file and command-line arguments.

    Args:
        config_path: Path to configuration file (optional)
        args: Command-line arguments

    Returns:
        Merged configuration

    Raises:
        ConfigurationError: If configuration is invalid
    """
    # Start with defaults
    config = Config()

    # Load from file if provided
    if config_path:
        try:
            import json
            with open(config_path, 'r') as f:
                config_data = json.load(f)
                # Merge config_data into config (simplified for now)
                if 'storage' in config_data:
                    config.storage = [
                        StorageConfig(**s) if isinstance(s, dict) else s
                        for s in config_data['storage']
                    ]
        except Exception as e:
            raise ConfigurationError(f"Failed to load config file: {e}") from e

    # Override with command-line arguments
    if args.storage:
        backends = args.storage.split(',')
        config.storage = []
        for backend in backends:
            if backend == 'jsonl':
                path = args.jsonl_path or '.commit-reflections.jsonl'
                config.storage.append(StorageConfig(
                    backend='jsonl',
                    path=path,
                    enabled=True,
                ))
            elif backend == 'database':
                path = args.db_path or '~/.commit-reflect/reflections.db'
                config.storage.append(StorageConfig(
                    backend='sqlite',
                    path=path,
                    enabled=True,
                ))

    # Ensure at least one storage backend
    if not config.storage:
        config.storage = [StorageConfig(
            backend='jsonl',
            path='.commit-reflections.jsonl',
            enabled=True,
        )]

    return config


def run_interactive_mode(args: Namespace) -> int:
    """
    Run the interactive CLI reflection session.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        # Load configuration
        config = load_config(args.config, args)

        # Get commit context
        try:
            commit_context = get_commit_context(
                commit_hash=args.commit or "HEAD",
                project=args.project,
                branch=args.branch,
            )
        except GitError as e:
            display_error(f"Failed to get commit information: {e}")
            return 1

        # Display welcome (use project from args or infer from repo)
        project_name = args.project
        if not project_name:
            try:
                from packages.cli.src.git_utils import get_repository_root
                repo_root = get_repository_root()
                project_name = repo_root.name
            except:
                project_name = "unknown"

        display_welcome(commit_context.commit_hash, project_name)

        # Create reflection session
        question_set = create_default_question_set()
        session = ReflectionSession(
            commit_context=commit_context,
            question_set=question_set,
            config=config,
        )

        # Question loop
        while not session.is_complete():
            current_question = session.get_current_question()
            if not current_question:
                break

            progress = session.get_progress()

            # Prompt for answer with validation loop
            answer_accepted = False
            while not answer_accepted:
                answer = prompt_for_answer(current_question, progress)

                # Handle skip for optional questions
                if answer is None and not current_question.required:
                    success, error = session.skip_current_question()
                    if success:
                        answer_accepted = True
                    else:
                        display_error(error)
                        return 1
                elif answer is None:
                    display_validation_error("This question is required")
                else:
                    # Try to answer the question
                    success, error = session.answer_current_question(answer)
                    if success:
                        answer_accepted = True
                    else:
                        display_validation_error(error)

        # Show summary
        display_summary(
            session.state.answers,
            session.questions
        )

        # Confirm submission
        if not confirm_submission():
            print("\nReflection cancelled. No data was saved.")
            return 0

        # Convert to Reflection object
        reflection = session.to_reflection()

        # Save to storage backends
        storage_info_lines = []
        for storage_config in config.storage:
            if not storage_config.enabled:
                continue

            try:
                storage = create_storage_from_config(storage_config)
                success = storage.write(reflection.to_dict())
                storage.close()

                if success:
                    backend_name = storage_config.backend
                    if backend_name == 'jsonl':
                        storage_info_lines.append(f"✓ Saved to JSONL: {storage_config.path}")
                    elif backend_name == 'sqlite':
                        storage_info_lines.append(f"✓ Saved to database: {storage_config.path}")
                    else:
                        storage_info_lines.append(f"✓ Saved to {backend_name}")
                else:
                    display_error(f"Failed to write to {storage_config.backend} storage")
                    return 1

            except Exception as e:
                display_error(f"Storage error ({storage_config.backend}): {e}")
                return 1

        # Display completion
        storage_info = "\n".join(storage_info_lines)
        display_completion_message(storage_info)

        return 0

    except KeyboardInterrupt:
        print("\n\nReflection cancelled by user.")
        return 130  # Standard exit code for Ctrl+C

    except Exception as e:
        display_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc(file=sys.stderr)
        return 1
