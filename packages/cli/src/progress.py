"""Progress indicators and user feedback."""

import sys
from typing import Optional


class ProgressIndicator:
    """
    Provides user-friendly progress indicators and messages.

    Displays question progress, helpful context, and clear feedback.
    """

    def __init__(self, total_questions: int = 5, use_color: bool = True):
        """
        Initialize progress indicator.

        Args:
            total_questions: Total number of questions in reflection
            use_color: Whether to use ANSI color codes
        """
        self.total_questions = total_questions
        self.current_question = 0
        self.use_color = use_color and sys.stdout.isatty()

        # ANSI color codes
        self.BLUE = "\033[94m" if self.use_color else ""
        self.GREEN = "\033[92m" if self.use_color else ""
        self.YELLOW = "\033[93m" if self.use_color else ""
        self.RED = "\033[91m" if self.use_color else ""
        self.BOLD = "\033[1m" if self.use_color else ""
        self.RESET = "\033[0m" if self.use_color else ""

    def show_welcome(self, project: str, commit_hash: str) -> None:
        """
        Display welcome message.

        Args:
            project: Project name
            commit_hash: Commit hash
        """
        print(f"\n{self.BOLD}{self.BLUE}=== Commit Reflection ==={self.RESET}")
        print(f"Project: {self.BOLD}{project}{self.RESET}")
        print(f"Commit:  {self.BOLD}{commit_hash[:8]}{self.RESET}")
        print(f"\n{self.total_questions} quick questions to capture your experience.\n")

    def show_question(
        self,
        question_num: int,
        question_text: str,
        help_text: Optional[str] = None,
        optional: bool = False
    ) -> None:
        """
        Display a question with progress indicator.

        Args:
            question_num: Current question number (1-indexed)
            question_text: Question text to display
            help_text: Optional help text
            optional: Whether the question is optional
        """
        self.current_question = question_num

        # Progress indicator
        progress = f"[{question_num}/{self.total_questions}]"
        optional_tag = f" {self.YELLOW}(optional){self.RESET}" if optional else ""

        print(f"\n{self.BOLD}{progress}{self.RESET} {question_text}{optional_tag}")

        if help_text:
            print(f"{self.BLUE}ℹ  {help_text}{self.RESET}")

    def show_error(self, error_message: str, help_text: Optional[str] = None) -> None:
        """
        Display an error message.

        Args:
            error_message: Error message to display
            help_text: Optional help text for recovery
        """
        print(f"{self.RED}✗ {error_message}{self.RESET}")
        if help_text:
            print(f"{self.YELLOW}→ {help_text}{self.RESET}")

    def show_success(self, message: str = "Reflection saved successfully!") -> None:
        """
        Display success message.

        Args:
            message: Success message to display
        """
        print(f"\n{self.GREEN}✓ {message}{self.RESET}\n")

    def show_warning(self, message: str) -> None:
        """
        Display warning message.

        Args:
            message: Warning message to display
        """
        print(f"{self.YELLOW}⚠  {message}{self.RESET}")

    def show_storage_status(
        self,
        successful_backends: list,
        failed_backends: list
    ) -> None:
        """
        Display storage operation status.

        Args:
            successful_backends: List of successful storage backends
            failed_backends: List of (backend, error) tuples for failures
        """
        if successful_backends:
            backends_str = ", ".join(str(b) for b in successful_backends)
            print(f"{self.GREEN}✓ Saved to: {backends_str}{self.RESET}")

        if failed_backends:
            print(f"{self.YELLOW}⚠  Some backends failed:{self.RESET}")
            for backend, error in failed_backends:
                print(f"   {self.RED}✗{self.RESET} {backend}: {error}")

    def show_cancel(self) -> None:
        """Display cancellation message."""
        print(f"\n{self.YELLOW}Reflection cancelled. No data was saved.{self.RESET}\n")

    def prompt_recovery(self, session_info: dict) -> bool:
        """
        Prompt user to recover a previous session.

        Args:
            session_info: Information about recoverable session

        Returns:
            True if user wants to recover, False otherwise
        """
        print(f"\n{self.YELLOW}⚠  Found incomplete reflection session:{self.RESET}")
        print(f"   Project: {session_info.get('project', 'unknown')}")
        print(f"   Commit:  {session_info.get('commit', 'unknown')}")
        print(f"   Progress: {session_info.get('questions_answered', 0)}/{self.total_questions} questions")

        response = input(f"\n{self.BOLD}Recover this session? [y/N]:{self.RESET} ").strip().lower()
        return response in ["y", "yes"]

    def show_progress_bar(self, current: int, total: int, width: int = 40) -> None:
        """
        Display a progress bar.

        Args:
            current: Current progress value
            total: Total value
            width: Width of progress bar in characters
        """
        if total == 0:
            percent = 0
        else:
            percent = int((current / total) * 100)

        filled = int((current / total) * width) if total > 0 else 0
        bar = "█" * filled + "░" * (width - filled)

        print(f"\r{self.BLUE}[{bar}]{self.RESET} {percent}%", end="", flush=True)

        if current >= total:
            print()  # New line when complete
