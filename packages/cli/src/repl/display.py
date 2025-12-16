"""Terminal display helpers for REPL mode."""

from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from shared.types.question import Question

from .queue import CommitQueue, QueuedCommit


class REPLDisplay:
    """Terminal display helpers for consistent REPL output.

    Provides formatted output for all REPL states and events.
    """

    # Display constants
    SEPARATOR = "=" * 60
    THIN_SEPARATOR = "-" * 60

    def show_welcome(self, project: str, port: int) -> None:
        """Display welcome banner when REPL starts.

        Args:
            project: Project name
            port: Port server is listening on
        """
        print()
        print(self.SEPARATOR)
        print("COMMIT REFLECT REPL")
        print(self.SEPARATOR)
        print(f"Project: {project}")
        print(f"Listening for commits on port {port}")
        print()
        print("Commands:")
        print("  'status'  - Show queue status")
        print("  'quit'    - Exit REPL")
        print("  'help'    - Show this help")
        print(self.SEPARATOR)
        print()

    def show_idle_prompt(self) -> None:
        """Show idle state indicator (waiting for commits)."""
        print("\r[Waiting for commits...] ", end="", flush=True)

    def show_commit_detected(
        self,
        commit: QueuedCommit,
        pending_count: int = 0,
    ) -> None:
        """Display commit detection notification.

        Args:
            commit: The detected commit
            pending_count: Number of other commits in queue
        """
        print()  # Clear any inline prompt
        print(self.THIN_SEPARATOR)
        print(f"Commit detected: {commit.short_hash}")
        print(f"  Project: {commit.project}")
        print(f"  Branch:  {commit.branch}")
        if pending_count > 0:
            print(f"  ({pending_count} more commit(s) in queue)")
        print(self.THIN_SEPARATOR)

    def show_queued_notification(
        self,
        commit: QueuedCommit,
        queue_size: int,
    ) -> None:
        """Show inline notification when commit is queued during reflection.

        Args:
            commit: The queued commit
            queue_size: Total commits now in queue
        """
        print(f"\n[Commit {commit.short_hash} queued ({queue_size} pending)]")

    def show_question(
        self,
        question_text: str,
        question_number: int,
        total_questions: int,
        help_text: str | None = None,
        required: bool = True,
        question: Optional["Question"] = None,
    ) -> None:
        """Display a reflection question.

        Args:
            question_text: The question to display
            question_number: Current question number (1-indexed)
            total_questions: Total number of questions
            help_text: Optional help/hint text
            required: Whether question is required
            question: Full Question object for type-specific display
        """
        from shared.types.question import QuestionType

        print()
        print(f"[Question {question_number}/{total_questions}]")
        print(question_text)
        if help_text:
            print(f"  ({help_text})")

        # Show type-specific options/hints
        if question:
            allow_other = question.metadata and question.metadata.get("allow_other_text", False)
            if question.question_type == QuestionType.CHOICE and question.options:
                print("  Options:")
                for i, option in enumerate(question.options, 1):
                    if option == "Other" and allow_other:
                        print(f"    {i}. {option} (or type your own response)")
                    else:
                        print(f"    {i}. {option}")
            elif question.question_type == QuestionType.MULTICHOICE and question.options:
                hint = "enter numbers separated by commas"
                if allow_other:
                    hint += ", or type your own"
                print(f"  Options ({hint}):")
                for i, option in enumerate(question.options, 1):
                    if option == "Other" and allow_other:
                        print(f"    {i}. {option} (or type your own)")
                    else:
                        print(f"    {i}. {option}")
            elif question.question_type in (QuestionType.SCALE, QuestionType.RATING):
                print(f"  Range: {question.min_value}-{question.max_value}")
            elif question.question_type == QuestionType.MULTILINE:
                print("  (Enter your response, press Enter twice to finish)")

        if not required:
            print("  [Optional - press Enter to skip]")

    def show_validation_error(self, error: str | None) -> None:
        """Display validation error for invalid answer.

        Args:
            error: Error message to display
        """
        if error:
            print(f"Invalid: {error}. Please try again.")

    def show_summary(
        self,
        answers: dict[str, Any],
        questions: list[dict[str, Any]],
    ) -> None:
        """Display reflection summary before saving.

        Args:
            answers: Dict mapping question_id to answer
            questions: List of question dicts with 'id' and 'text' keys
        """
        print()
        print(self.SEPARATOR)
        print("REFLECTION SUMMARY")
        print(self.SEPARATOR)
        for q in questions:
            q_id = q.get("id", "")
            q_text = q.get("text", "Unknown question")
            if q_id in answers:
                answer = answers[q_id]
                # Truncate long answers for display
                if isinstance(answer, str) and len(answer) > 100:
                    answer = answer[:97] + "..."
                print(f"{q_text}")
                print(f"  -> {answer}")
                print()
        print(self.SEPARATOR)

    def show_completion(self) -> None:
        """Display completion message after saving."""
        print()
        print("Reflection saved successfully!")
        print()

    def show_cancelled(self) -> None:
        """Display message when reflection is cancelled."""
        print()
        print("Reflection cancelled.")
        print()

    def show_queue_status(self, queue: CommitQueue) -> None:
        """Display current queue status.

        Args:
            queue: The commit queue to display
        """
        print()
        if queue.size == 0:
            print("Queue status: Empty (no pending commits)")
        else:
            print(f"Queue status: {queue.size} pending commit(s)")
            for commit in queue.get_all():
                time_str = commit.received_at.strftime("%H:%M:%S")
                print(f"  - {commit.short_hash} ({commit.project}/{commit.branch}) at {time_str}")

        if queue.current:
            print(f"Currently processing: {queue.current.short_hash}")
        print()

    def show_help(self) -> None:
        """Display help information."""
        print()
        print("Available commands:")
        print("  status  - Show pending commits in queue")
        print("  quit    - Exit the REPL")
        print("  help    - Show this help message")
        print()
        print("During reflection:")
        print("  - Answer each question as prompted")
        print("  - Press Enter to skip optional questions")
        print("  - Press Ctrl+C to cancel current reflection")
        print()

    def show_error(self, message: str) -> None:
        """Display error message.

        Args:
            message: Error message to display
        """
        print(f"\nError: {message}\n")

    def show_message(self, message: str) -> None:
        """Display generic message.

        Args:
            message: Message to display
        """
        print(message)

    def show_goodbye(self) -> None:
        """Display exit message."""
        print()
        print("Goodbye!")
        print()

    def clear_line(self) -> None:
        """Clear the current line (for updating inline prompts)."""
        print("\r" + " " * 60 + "\r", end="", flush=True)
