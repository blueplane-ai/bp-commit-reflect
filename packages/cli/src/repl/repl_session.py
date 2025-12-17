"""Main REPL orchestration for commit-reflect.

This module ties together all REPL components to provide a persistent
terminal interface that listens for git commits and prompts for reflections.
"""

import asyncio
import signal
from pathlib import Path

from shared.storage.factory import create_storage_from_config
from shared.types.config import Config, StorageBackendType, StorageConfig
from shared.types.question import create_default_question_set

from ..git_utils import GitError, get_commit_context
from ..session import ReflectionSession
from .display import REPLDisplay
from .input_handler import AsyncInputHandler
from .queue import CommitQueue, QueuedCommit
from .server import CommitNotificationServer
from .state_machine import REPLState, StateMachine


class REPLMode:
    """Main REPL orchestration class.

    Ties together the HTTP server, state machine, commit queue,
    input handler, and display to provide an interactive REPL
    for commit reflections.
    """

    def __init__(
        self,
        project: str,
        port: int = 9123,
        config: Config | None = None,
        working_dir: Path | None = None,
    ):
        """Initialize REPL mode.

        Args:
            project: Project name
            port: Port for HTTP server (default: 9123)
            config: Configuration object (optional)
            working_dir: Working directory for git operations
        """
        self.project = project
        self.port = port
        self.config = config
        self.working_dir = working_dir or Path.cwd()

        # Initialize components
        self.state_machine = StateMachine()
        self.queue = CommitQueue()
        self.server = CommitNotificationServer(
            port=port,
            on_commit=self._on_commit_received,
        )
        self.input_handler = AsyncInputHandler()
        self.display = REPLDisplay()

        # Current reflection session (if any)
        self._current_session: ReflectionSession | None = None

        # Control flags
        self._should_exit = False
        self._interrupted = False

    async def run(self) -> int:
        """Run the main REPL loop.

        Returns:
            Exit code (0 for success)
        """
        try:
            # Set up signal handlers
            self._setup_signals()

            # Start components
            await self.server.start()
            await self.input_handler.start()

            # Show welcome
            self.display.show_welcome(self.project, self.port)

            # Main loop
            while not self._should_exit:
                try:
                    await self._process_current_state()
                except asyncio.CancelledError:
                    break
                except KeyboardInterrupt:
                    self._handle_interrupt()

            return 0

        except OSError as e:
            if "Address already in use" in str(e):
                self.display.show_error(
                    f"Port {self.port} is already in use. " f"Try a different port with --port"
                )
            else:
                self.display.show_error(str(e))
            return 1

        except Exception as e:
            self.display.show_error(f"Unexpected error: {e}")
            return 1

        finally:
            await self._cleanup()

    async def _process_current_state(self) -> None:
        """Process the current state machine state."""
        state = self.state_machine.state

        if state == REPLState.HOME:
            await self._handle_home_state()
        elif state == REPLState.PROMPTING:
            await self._handle_prompting_state()
        elif state == REPLState.IN_REFLECTION:
            await self._handle_reflection_state()
        elif state == REPLState.COMPLETING:
            await self._handle_completing_state()

    async def _handle_home_state(self) -> None:
        """Handle HOME/idle state."""
        # Check if there are queued commits
        if not self.queue.is_empty:
            self.state_machine.transition_to(REPLState.PROMPTING)
            return

        # Show idle prompt and wait for input or timeout
        self.display.show_idle_prompt()

        # Wait for user input with short timeout to allow checking queue
        response = await self.input_handler.get_input(timeout=0.5)

        if response is not None:
            await self._handle_home_command(response)

    async def _handle_home_command(self, command: str) -> None:
        """Handle a command entered at home state.

        Args:
            command: The command entered by user
        """
        command = command.strip().lower()

        if command in ("q", "quit", "exit"):
            self.display.show_goodbye()
            self._should_exit = True

        elif command == "status":
            self.display.clear_line()
            self.display.show_queue_status(self.queue)

        elif command == "help":
            self.display.clear_line()
            self.display.show_help()

        elif command:
            # Unknown command - show help hint
            self.display.clear_line()
            self.display.show_message(
                f"Unknown command: '{command}'. Type 'help' for available commands."
            )

    async def _handle_prompting_state(self) -> None:
        """Handle PROMPTING state - ask user to start reflection."""
        # Get the next commit from queue
        commit = self.queue.dequeue()
        if not commit:
            self.state_machine.transition_to(REPLState.HOME)
            return

        # Show commit detection
        self.display.show_commit_detected(commit, self.queue.size)

        # Ask user if they want to reflect
        response = await self.input_handler.prompt_yes_no(
            "Start reflection? (y/n): ",
            default=True,
        )

        if response is True:
            # Try to start reflection
            success = await self._start_reflection(commit)
            if success:
                self.state_machine.transition_to(REPLState.IN_REFLECTION)
            else:
                # Failed to start, go back to home
                self.queue.clear_current()
                self.state_machine.transition_to(REPLState.HOME)
        else:
            # User declined, check for more commits
            self.queue.clear_current()
            if self.queue.is_empty:
                self.state_machine.transition_to(REPLState.HOME)
            else:
                # More commits in queue, stay in prompting
                pass  # Will process next commit on next iteration

    async def _start_reflection(self, commit: QueuedCommit) -> bool:
        """Start a new reflection session.

        Args:
            commit: The commit to reflect on

        Returns:
            True if session started successfully
        """
        try:
            # Use repo_path from commit if provided, otherwise fall back to working_dir
            repo_dir = Path(commit.repo_path) if commit.repo_path else self.working_dir

            # Get commit context from git
            commit_context = get_commit_context(
                commit_hash=commit.commit_hash,
                project=commit.project,
                branch=commit.branch,
                cwd=repo_dir,
            )

            # Create question set
            question_set = create_default_question_set()

            # Create reflection session
            self._current_session = ReflectionSession(
                commit_context=commit_context,
                question_set=question_set,
                config=self.config,
            )

            return True

        except GitError as e:
            self.display.show_error(f"Failed to get commit info: {e}")
            return False
        except Exception as e:
            self.display.show_error(f"Failed to start reflection: {e}")
            return False

    async def _handle_reflection_state(self) -> None:
        """Handle IN_REFLECTION state - question flow."""
        if not self._current_session:
            self.state_machine.transition_to(REPLState.HOME)
            return

        # Get current question
        current_question = self._current_session.get_current_question()
        if not current_question:
            # All questions answered
            self.state_machine.transition_to(REPLState.COMPLETING)
            return

        # Get progress
        current_num, total = self._current_session.get_progress()

        # Show question
        self.display.show_question(
            question_text=current_question.text,
            question_number=current_num,
            total_questions=total,
            help_text=current_question.help_text,
            required=current_question.required,
            question=current_question,
        )

        # Get answer
        answer = await self.input_handler.prompt("> ")

        if answer is None:
            # Timeout or cancelled - stay in state
            return

        # Handle skip for optional questions
        if answer == "" and not current_question.required:
            success, error = self._current_session.skip_current_question()
            if not success:
                self.display.show_validation_error(error)
        else:
            # Submit answer
            success, error = self._current_session.answer_current_question(answer)
            if not success:
                self.display.show_validation_error(error)

    async def _handle_completing_state(self) -> None:
        """Handle COMPLETING state - save and finish."""
        if not self._current_session:
            self.state_machine.transition_to(REPLState.HOME)
            return

        # Build summary data for display
        answers = self._current_session.state.answers
        questions = [{"id": q.id, "text": q.text} for q in self._current_session.questions]

        # Show summary
        self.display.show_summary(answers, questions)

        # Ask to save
        response = await self.input_handler.prompt_yes_no(
            "Save reflection? (y/n): ",
            default=True,
        )

        if response is True:
            # Save reflection
            success = await self._save_reflection()
            if success:
                self.display.show_completion()
            else:
                self.display.show_error("Failed to save reflection")
        else:
            self.display.show_cancelled()

        # Clean up session
        self._current_session = None
        self.queue.clear_current()

        # Check for more commits
        if self.queue.is_empty:
            self.state_machine.transition_to(REPLState.HOME)
        else:
            self.state_machine.transition_to(REPLState.PROMPTING)

    async def _save_reflection(self) -> bool:
        """Save the current reflection to storage.

        Returns:
            True if saved successfully
        """
        if not self._current_session:
            return False

        try:
            # Convert session to reflection
            reflection = self._current_session.to_reflection()

            # Get storage config
            storage_configs = self._get_storage_configs()

            # Write to each enabled backend
            any_success = False
            for storage_config in storage_configs:
                if not storage_config.enabled:
                    continue

                try:
                    storage = create_storage_from_config(storage_config)
                    storage.write(reflection.to_dict())
                    storage.close()
                    any_success = True
                except Exception as e:
                    self.display.show_error(
                        f"Failed to write to {storage_config.backend_type.value}: {e}"
                    )

            return any_success

        except Exception as e:
            self.display.show_error(f"Failed to save reflection: {e}")
            return False

    def _get_storage_configs(self) -> list[StorageConfig]:
        """Get storage configurations.

        Returns:
            List of storage configs to use
        """
        if self.config and hasattr(self.config, "storage_backends"):
            return self.config.storage_backends

        # Default: JSONL only
        return [
            StorageConfig(
                backend_type=StorageBackendType.JSONL,
                enabled=True,
                path=".commit-reflections.jsonl",
            )
        ]

    def _on_commit_received(self, commit: QueuedCommit) -> None:
        """Handle incoming commit notification from HTTP server.

        Args:
            commit: The received commit
        """
        queue_size = self.queue.enqueue(commit)

        if self.state_machine.is_busy():
            # Show inline notification during reflection
            self.display.show_queued_notification(commit, queue_size)
        elif self.state_machine.is_idle():
            # Trigger transition to prompting
            self.state_machine.transition_to(REPLState.PROMPTING)

    def _handle_interrupt(self) -> None:
        """Handle Ctrl+C interrupt."""
        state = self.state_machine.state

        if state == REPLState.IN_REFLECTION:
            # Cancel current reflection
            self.display.show_cancelled()
            self._current_session = None
            self.queue.clear_current()

            # Check for more commits
            if self.queue.is_empty:
                self.state_machine.transition_to(REPLState.HOME)
            else:
                self.state_machine.transition_to(REPLState.PROMPTING)

        elif state == REPLState.COMPLETING:
            # Cancel save, go back
            self.display.show_cancelled()
            self._current_session = None
            self.queue.clear_current()
            self.state_machine.transition_to(REPLState.HOME)

        else:
            # Exit REPL
            self.display.show_goodbye()
            self._should_exit = True

    def _setup_signals(self) -> None:
        """Set up signal handlers for graceful shutdown."""
        loop = asyncio.get_event_loop()

        def handle_sigint():
            self._handle_interrupt()

        try:
            loop.add_signal_handler(signal.SIGINT, handle_sigint)
        except NotImplementedError:
            # Windows doesn't support add_signal_handler
            pass

    async def _cleanup(self) -> None:
        """Clean up resources on exit."""
        await self.input_handler.stop()
        await self.server.stop()


async def run_repl_mode(
    project: str,
    port: int = 9123,
    config: Config | None = None,
    working_dir: Path | None = None,
) -> int:
    """Entry point for REPL mode.

    Args:
        project: Project name
        port: HTTP server port
        config: Configuration object
        working_dir: Working directory for git operations

    Returns:
        Exit code
    """
    repl = REPLMode(
        project=project,
        port=port,
        config=config,
        working_dir=working_dir,
    )
    return await repl.run()
