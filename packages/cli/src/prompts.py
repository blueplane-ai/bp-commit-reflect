"""
Interactive prompting system for collecting reflection answers.

This module provides functions for presenting questions to users and
collecting their answers in an interactive terminal session.
"""

import sys
from typing import Optional, Any
from shared.types.question import Question, QuestionType
from cli.src.progress import ProgressIndicator


def format_question_prompt(question: Question, progress: tuple[int, int]) -> str:
    """
    Format a question for display.

    Args:
        question: Question to format
        progress: Tuple of (current, total) for progress display

    Returns:
        Formatted question string
    """
    current, total = progress
    lines = []

    # Progress indicator
    lines.append(f"\n[Question {current} of {total}]")
    lines.append("=" * 60)

    # Question text
    lines.append(f"\n{question.text}")

    # Help text if available
    if question.help_text:
        lines.append(f"  ({question.help_text})")

    # Type-specific hints
    if question.question_type == QuestionType.SCALE:
        lines.append(f"  Range: {question.min_value}-{question.max_value}")
    elif question.question_type == QuestionType.RATING:
        lines.append(f"  Range: {question.min_value}-{question.max_value}")
    elif question.question_type == QuestionType.BOOLEAN:
        lines.append("  Enter: yes/no or y/n")
    elif question.question_type == QuestionType.CHOICE:
        lines.append("  Options:")
        for i, option in enumerate(question.options or [], 1):
            lines.append(f"    {i}. {option}")
    elif question.question_type == QuestionType.MULTILINE:
        lines.append("  (Enter an empty line to finish)")

    # Required indicator
    if question.required:
        lines.append("  [Required]")
    else:
        lines.append("  [Optional - press Enter to skip]")

    lines.append("")  # Blank line before input

    return "\n".join(lines)


def collect_text_answer(question: Question) -> str:
    """
    Collect a single-line text answer.

    Args:
        question: Question being answered

    Returns:
        The answer text
    """
    if question.placeholder:
        prompt = f"> {question.placeholder}\n> "
    else:
        prompt = "> "

    answer = input(prompt).strip()
    return answer


def collect_multiline_answer(question: Question) -> str:
    """
    Collect a multi-line text answer.

    Args:
        question: Question being answered

    Returns:
        The answer text (multiple lines joined)
    """
    print("> Enter your answer (empty line to finish):")

    if question.placeholder:
        print(f"> {question.placeholder}")

    lines = []
    while True:
        try:
            line = input("> ")
            if not line.strip():
                break
            lines.append(line)
        except EOFError:
            break

    return "\n".join(lines)


def collect_scale_answer(question: Question) -> str:
    """
    Collect a scale/rating answer.

    Args:
        question: Question being answered

    Returns:
        The answer as string (will be validated later)
    """
    prompt = f"> Enter {question.min_value}-{question.max_value}: "
    answer = input(prompt).strip()
    return answer


def collect_boolean_answer(question: Question) -> str:
    """
    Collect a yes/no answer.

    Args:
        question: Question being answered

    Returns:
        The answer as string (will be normalized to yes/no)
    """
    prompt = "> Enter yes/no (or y/n): "
    answer = input(prompt).strip().lower()

    # Normalize common inputs
    if answer in ['y', 'yes', 'true', '1']:
        return 'yes'
    elif answer in ['n', 'no', 'false', '0']:
        return 'no'

    return answer


def collect_choice_answer(question: Question) -> str:
    """
    Collect a single choice answer.

    Args:
        question: Question being answered

    Returns:
        The selected option
    """
    options = question.options or []

    while True:
        prompt = f"> Enter 1-{len(options)} or type the option: "
        answer = input(prompt).strip()

        # Check if it's a number
        if answer.isdigit():
            idx = int(answer) - 1
            if 0 <= idx < len(options):
                return options[idx]

        # Check if it matches an option
        if answer in options:
            return answer

        # Check case-insensitive match
        for option in options:
            if answer.lower() == option.lower():
                return option

        print(f"  Invalid choice. Please select from: {', '.join(options)}")


def prompt_for_answer(question: Question, progress: tuple[int, int]) -> Optional[str]:
    """
    Display a question and collect the answer.

    Args:
        question: Question to ask
        progress: Progress tuple (current, total)

    Returns:
        The answer string, or None if skipped
    """
    # Display the question
    print(format_question_prompt(question, progress))

    try:
        # Collect answer based on question type
        if question.question_type in [QuestionType.TEXT]:
            answer = collect_text_answer(question)
        elif question.question_type == QuestionType.MULTILINE:
            answer = collect_multiline_answer(question)
        elif question.question_type in [QuestionType.SCALE, QuestionType.RATING]:
            answer = collect_scale_answer(question)
        elif question.question_type == QuestionType.BOOLEAN:
            answer = collect_boolean_answer(question)
        elif question.question_type == QuestionType.CHOICE:
            answer = collect_choice_answer(question)
        else:
            # Default to text input
            answer = collect_text_answer(question)

        # Handle optional questions
        if not answer and not question.required:
            return None

        return answer

    except KeyboardInterrupt:
        print("\n\nReflection cancelled by user.")
        sys.exit(1)
    except EOFError:
        print("\n\nReflection cancelled (EOF).")
        sys.exit(1)


def display_summary(answers: dict, questions: list) -> None:
    """
    Display a summary of all answers.

    Args:
        answers: Dictionary of question_id -> answer
        questions: List of Question objects
    """
    print("\n" + "=" * 60)
    print("REFLECTION SUMMARY")
    print("=" * 60 + "\n")

    question_map = {q.id: q for q in questions}

    for question_id, answer in answers.items():
        question = question_map.get(question_id)
        if question:
            print(f"{question.text}")
            print(f"  → {answer}")
            print()


def confirm_submission() -> bool:
    """
    Ask user to confirm submission.

    Returns:
        True if user confirms, False otherwise
    """
    print("\n" + "=" * 60)
    print("Ready to submit your reflection?")
    print("=" * 60)

    while True:
        response = input("\nSubmit reflection? (yes/no): ").strip().lower()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        else:
            print("Please enter 'yes' or 'no'")


def display_welcome(commit_hash: str, project: str) -> None:
    """
    Display welcome message at session start.

    Args:
        commit_hash: Hash of the commit being reflected on
        project: Project name
    """
    print("\n" + "=" * 60)
    print("COMMIT REFLECTION")
    print("=" * 60)
    print(f"\nProject: {project}")
    print(f"Commit: {commit_hash[:12]}...")
    print("\nThis reflection will help document your development process.")
    print("Answer thoughtfully - these insights are valuable for your team.")
    print("=" * 60)


def display_completion_message(storage_info: str) -> None:
    """
    Display completion message after successful submission.

    Args:
        storage_info: Information about where reflection was stored
    """
    print("\n" + "=" * 60)
    print("✓ REFLECTION SAVED")
    print("=" * 60)
    print(f"\n{storage_info}")
    print("\nThank you for taking time to reflect on your work!")
    print("=" * 60 + "\n")


def display_error(error_message: str) -> None:
    """
    Display an error message.

    Args:
        error_message: Error message to display
    """
    print(f"\n✗ Error: {error_message}\n", file=sys.stderr)


def display_validation_error(error_message: str) -> None:
    """
    Display a validation error and prompt to try again.

    Args:
        error_message: Validation error message
    """
    print(f"\n⚠ Invalid answer: {error_message}", file=sys.stderr)
    print("Please try again.\n", file=sys.stderr)
