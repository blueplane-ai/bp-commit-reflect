"""Input validation for reflection questions and answers."""

from typing import Any

from shared.types.question import Question, QuestionType


class ValidationError(Exception):
    """Raised when input validation fails."""

    def __init__(self, message: str, help_text: str | None = None):
        super().__init__(message)
        self.message = message
        self.help_text = help_text


def validate_scale(
    value: Any, min_value: int = 1, max_value: int = 5, question_id: str | None = None
) -> tuple[int, str | None]:
    """
    Validate scale (numeric) input.

    Args:
        value: User input value
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        question_id: Question identifier for error messages

    Returns:
        Tuple of (validated_value, error_message)
        error_message is None if validation succeeds
    """
    try:
        # Try to convert to integer
        num_value = int(value)

        # Check range
        if num_value < min_value or num_value > max_value:
            return None, f"Value must be between {min_value} and {max_value}, got {num_value}"

        return num_value, None

    except ValueError:
        return None, f"Invalid number: '{value}'. Enter a number from {min_value} to {max_value}"


def validate_text(
    value: Any,
    max_length: int | None = None,
    min_length: int | None = None,
    allow_empty: bool = False,
    question_id: str | None = None,
) -> tuple[str, str | None]:
    """
    Validate text input.

    Args:
        value: User input value
        max_length: Maximum allowed length (optional)
        min_length: Minimum required length (optional)
        allow_empty: Whether empty strings are allowed
        question_id: Question identifier for error messages

    Returns:
        Tuple of (validated_value, error_message)
        error_message is None if validation succeeds
    """
    # Convert to string and strip whitespace
    text_value = str(value).strip()

    # Check if empty
    if not text_value:
        if allow_empty:
            return "", None
        else:
            return None, "This field cannot be empty. Please provide a response"

    # Check minimum length
    if min_length is not None and len(text_value) < min_length:
        return None, f"Response too short: {len(text_value)} characters (minimum: {min_length})"

    # Check maximum length
    if max_length is not None and len(text_value) > max_length:
        return None, f"Response too long: {len(text_value)} characters (maximum: {max_length})"

    return text_value, None


def validate_choice(
    value: Any, options: list, question_id: str | None = None, allow_other_text: bool = False
) -> tuple[str, str | None]:
    """
    Validate choice (single selection) input.

    Accepts either:
    - A numeric index (1-based)
    - The option text itself (case-insensitive match)
    - Freeform text if allow_other_text is True (stored as "Other: <text>")

    Args:
        value: User input value
        options: List of valid option strings
        question_id: Question identifier for error messages
        allow_other_text: If True, accept freeform text as "Other: <text>"

    Returns:
        Tuple of (validated_value, error_message)
    """
    answer = str(value).strip()

    if not answer:
        return None, "Please select an option"

    # Try numeric input first (1-based index)
    if answer.isdigit():
        idx = int(answer) - 1
        if 0 <= idx < len(options):
            return options[idx], None
        return None, f"Invalid option number: {answer}. Enter 1-{len(options)}"

    # Try exact match
    if answer in options:
        return answer, None

    # Try case-insensitive match
    answer_lower = answer.lower()
    for option in options:
        if option.lower() == answer_lower:
            return option, None

    # If allow_other_text, accept freeform input
    if allow_other_text:
        return f"Other: {answer}", None

    return None, f"Invalid option: '{answer}'. Enter 1-{len(options)} or the option name"


def validate_multichoice(
    value: Any, options: list, question_id: str | None = None, allow_other_text: bool = False
) -> tuple[list, str | None]:
    """
    Validate multichoice (multiple selection) input.

    Accepts:
    - Comma-separated numeric indices (1-based), e.g., "1,3,5"
    - Comma-separated option texts (case-insensitive)
    - Mix of both
    - Freeform text if allow_other_text is True (stored as "Other: <text>")

    Args:
        value: User input value
        options: List of valid option strings
        question_id: Question identifier for error messages
        allow_other_text: If True, accept freeform text as "Other: <text>"

    Returns:
        Tuple of (validated_values_list, error_message)
    """
    answer = str(value).strip()

    if not answer:
        return [], None

    # Split by comma
    parts = [p.strip() for p in answer.split(",")]
    selected = []

    for part in parts:
        if not part:
            continue

        # Try numeric input first (1-based index)
        if part.isdigit():
            idx = int(part) - 1
            if 0 <= idx < len(options):
                if options[idx] not in selected:
                    selected.append(options[idx])
                continue
            return None, f"Invalid option number: {part}. Enter 1-{len(options)}"

        # Try exact match
        if part in options:
            if part not in selected:
                selected.append(part)
            continue

        # Try case-insensitive match
        part_lower = part.lower()
        matched = False
        for option in options:
            if option.lower() == part_lower:
                if option not in selected:
                    selected.append(option)
                matched = True
                break

        if not matched:
            # If allow_other_text, accept freeform input
            if allow_other_text:
                other_value = f"Other: {part}"
                if other_value not in selected:
                    selected.append(other_value)
            else:
                return (
                    None,
                    f"Invalid option: '{part}'. Enter 1-{len(options)} or option names, comma-separated",
                )

    return selected, None


def validate_question_answer(
    question: Question | dict[str, Any], answer: Any
) -> tuple[Any, str | None]:
    """
    Validate an answer based on question configuration.

    Args:
        question: Question object or configuration dictionary
        answer: User's answer

    Returns:
        Tuple of (validated_answer, error_message)

    Raises:
        ValidationError: If validation fails
    """
    # Handle both Question objects and dictionaries
    if isinstance(question, Question):
        question_type = (
            question.question_type.value
            if isinstance(question.question_type, QuestionType)
            else question.question_type
        )
        question_id = question.id
        optional = not question.required
        min_val = question.min_value if question.min_value is not None else 1
        max_val = question.max_value if question.max_value is not None else 5
        options = question.options or []
        # Get validation rules if they exist
        validation_rules = question.validation_rules or {}
        max_length = validation_rules.get("max_length")
        min_length = validation_rules.get("min_length")
        # Check metadata for allow_other_text
        metadata = question.metadata or {}
        allow_other_text = metadata.get("allow_other_text", False)
    else:
        # Legacy dictionary support
        question_type = question.get("type", "text")
        question_id = question.get("id", "unknown")
        optional = question.get("optional", False)
        min_val = question.get("range", [1, 5])[0]
        max_val = question.get("range", [1, 5])[1]
        options = question.get("options", [])
        max_length = question.get("max_length")
        min_length = question.get("min_length")
        metadata = question.get("metadata", {})
        allow_other_text = metadata.get("allow_other_text", False)

    # Handle skip for optional questions
    if optional and (answer is None or str(answer).strip().lower() in ["skip", ""]):
        return None, None

    # Validate based on question type
    if question_type in ("scale", "rating"):
        return validate_scale(answer, min_val, max_val, question_id)

    elif question_type in ("text", "multiline"):
        return validate_text(
            answer,
            max_length=max_length,
            min_length=min_length,
            allow_empty=optional,
            question_id=question_id,
        )

    elif question_type == "choice":
        return validate_choice(answer, options, question_id, allow_other_text)

    elif question_type == "multichoice":
        return validate_multichoice(answer, options, question_id, allow_other_text)

    else:
        # Unknown question type - accept as-is
        return answer, None


def validate_config(config: dict[str, Any]) -> tuple[dict[str, Any], list]:
    """
    Validate configuration dictionary.

    Args:
        config: Configuration dictionary

    Returns:
        Tuple of (validated_config, list_of_warnings)
    """
    warnings = []
    validated = config.copy()

    # Validate storage configuration
    storage = validated.get("storage", ["jsonl"])
    if not isinstance(storage, list):
        storage = [storage]
    if "jsonl" not in storage:
        warnings.append("JSONL storage is recommended as a reliable default")

    validated["storage"] = storage

    # Validate paths
    if "jsonl_path" not in validated:
        validated["jsonl_path"] = ".commit-reflections.jsonl"

    if "db_path" not in validated:
        validated["db_path"] = "~/.commit-reflect/reflections.db"

    # Validate questions
    questions = validated.get("questions", [])
    if not questions:
        warnings.append("No questions defined - using defaults")

    # Ensure required questions are present (v2.0 question set)
    required_ids = [
        "work_type",
        "difficulty",
        "ai_effectiveness",
        "who_drove",
        "confidence",
        "experience",
        "outcome",
    ]
    question_ids = [q.get("id") for q in questions]

    for req_id in required_ids:
        if req_id not in question_ids:
            warnings.append(f"Required question '{req_id}' not found in configuration")

    return validated, warnings
