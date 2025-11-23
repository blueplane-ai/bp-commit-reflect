"""Input validation for reflection questions and answers."""

from typing import Any, Dict, Optional, Tuple


class ValidationError(Exception):
    """Raised when input validation fails."""

    def __init__(self, message: str, help_text: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.help_text = help_text


def validate_scale(
    value: Any,
    min_value: int = 1,
    max_value: int = 5,
    question_id: Optional[str] = None
) -> Tuple[int, Optional[str]]:
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

    Raises:
        ValidationError: If validation fails
    """
    try:
        # Try to convert to integer
        num_value = int(value)

        # Check range
        if num_value < min_value or num_value > max_value:
            raise ValidationError(
                f"Value must be between {min_value} and {max_value}, got {num_value}",
                help_text=f"Please enter a number from {min_value} to {max_value}"
            )

        return num_value, None

    except ValueError:
        raise ValidationError(
            f"Invalid number: '{value}'",
            help_text=f"Please enter a whole number between {min_value} and {max_value}"
        )


def validate_text(
    value: Any,
    max_length: Optional[int] = None,
    min_length: Optional[int] = None,
    allow_empty: bool = False,
    question_id: Optional[str] = None
) -> Tuple[str, Optional[str]]:
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

    Raises:
        ValidationError: If validation fails
    """
    # Convert to string and strip whitespace
    text_value = str(value).strip()

    # Check if empty
    if not text_value:
        if allow_empty:
            return "", None
        else:
            raise ValidationError(
                "This field cannot be empty",
                help_text="Please provide a response"
            )

    # Check minimum length
    if min_length is not None and len(text_value) < min_length:
        raise ValidationError(
            f"Response too short: {len(text_value)} characters (minimum: {min_length})",
            help_text=f"Please provide at least {min_length} characters"
        )

    # Check maximum length
    if max_length is not None and len(text_value) > max_length:
        raise ValidationError(
            f"Response too long: {len(text_value)} characters (maximum: {max_length})",
            help_text=f"Please limit your response to {max_length} characters"
        )

    return text_value, None


def validate_question_answer(
    question: Dict[str, Any],
    answer: Any
) -> Tuple[Any, Optional[str]]:
    """
    Validate an answer based on question configuration.

    Args:
        question: Question configuration dictionary
        answer: User's answer

    Returns:
        Tuple of (validated_answer, error_message)

    Raises:
        ValidationError: If validation fails
    """
    question_type = question.get("type", "text")
    question_id = question.get("id", "unknown")
    optional = question.get("optional", False)

    # Handle skip for optional questions
    if optional and (answer is None or str(answer).strip().lower() in ["skip", ""]):
        return None, None

    # Validate based on question type
    if question_type == "scale":
        min_val = question.get("range", [1, 5])[0]
        max_val = question.get("range", [1, 5])[1]
        return validate_scale(answer, min_val, max_val, question_id)

    elif question_type == "text":
        max_length = question.get("max_length")
        min_length = question.get("min_length")
        return validate_text(
            answer,
            max_length=max_length,
            min_length=min_length,
            allow_empty=optional,
            question_id=question_id
        )

    else:
        # Unknown question type - accept as-is
        return answer, None


def validate_config(config: Dict[str, Any]) -> Tuple[Dict[str, Any], list]:
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

    # Ensure required questions are present
    required_ids = ["ai_synergy", "confidence", "experience"]
    question_ids = [q.get("id") for q in questions]

    for req_id in required_ids:
        if req_id not in question_ids:
            warnings.append(f"Required question '{req_id}' not found in configuration")

    return validated, warnings
