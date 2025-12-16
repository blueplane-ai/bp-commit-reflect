"""
Question and answer types for the Commit Reflection System.

This module defines the structure of reflection questions, their types,
and how they are organized into question sets.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class QuestionType(str, Enum):
    """
    Types of questions that can be asked during reflection.

    Each type may have different validation rules and UI presentation.
    """

    TEXT = "text"  # Free-form text response
    MULTILINE = "multiline"  # Multi-line text response
    RATING = "rating"  # Numeric rating (e.g., 1-5)
    CHOICE = "choice"  # Single choice from options
    MULTICHOICE = "multichoice"  # Multiple choices from options
    BOOLEAN = "boolean"  # Yes/No question
    SCALE = "scale"  # Scaled response (e.g., 1-10)

    def __str__(self) -> str:
        """Return the string value of the enum."""
        return self.value

    @classmethod
    def from_string(cls, value: str) -> "QuestionType":
        """Create QuestionType from string value."""
        return cls(value)


@dataclass
class Question:
    """
    A single reflection question with its configuration.

    Attributes:
        id: Unique identifier for the question
        text: The question text to display
        question_type: The type of question (text, rating, etc.)
        required: Whether an answer is required
        help_text: Optional help text to display
        placeholder: Optional placeholder text for input
        default_value: Optional default value
        validation_rules: Optional validation rules
        options: For choice/multichoice questions, the available options
        min_value: For rating/scale questions, the minimum value
        max_value: For rating/scale questions, the maximum value
        order: Display order in the question sequence
        conditional: Optional function to determine if question should be shown
        metadata: Additional metadata about the question
    """

    id: str
    text: str
    question_type: QuestionType = QuestionType.TEXT
    required: bool = True
    help_text: Optional[str] = None
    placeholder: Optional[str] = None
    default_value: Optional[Any] = None
    validation_rules: Optional[Dict[str, Any]] = None
    options: Optional[List[str]] = None
    min_value: Optional[int] = None
    max_value: Optional[int] = None
    order: int = 0
    conditional: Optional[Callable[..., bool]] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Validate question configuration."""
        # Validate required fields
        if not self.id or not self.id.strip():
            raise ValueError("Question ID cannot be empty")
        if not self.text or not self.text.strip():
            raise ValueError("Question text cannot be empty")

        if isinstance(self.question_type, str):
            self.question_type = QuestionType(self.question_type)

        # Validate type-specific requirements
        if self.question_type in (QuestionType.CHOICE, QuestionType.MULTICHOICE):
            if not self.options:
                raise ValueError(f"Question {self.id}: {self.question_type} requires options")

        if self.question_type in (QuestionType.RATING, QuestionType.SCALE):
            if self.min_value is None or self.max_value is None:
                raise ValueError(
                    f"Question {self.id}: {self.question_type} requires min_value and max_value"
                )
            if self.min_value >= self.max_value:
                raise ValueError(f"Question {self.id}: min_value must be less than max_value")

    def to_dict(self) -> Dict[str, Any]:
        """Convert question to dictionary for serialization."""
        result = {
            "id": self.id,
            "text": self.text,
            "type": self.question_type.value,  # Use 'type' for external API
            "required": self.required,
            "order": self.order,
        }

        # Add optional fields
        if self.help_text:
            result["help_text"] = self.help_text
        if self.placeholder:
            result["placeholder"] = self.placeholder
        if self.default_value is not None:
            result["default_value"] = self.default_value
        if self.validation_rules:
            result["validation_rules"] = self.validation_rules
        if self.options:
            result["options"] = self.options
        if self.min_value is not None:
            result["min_value"] = self.min_value
        if self.max_value is not None:
            result["max_value"] = self.max_value
        if self.metadata:
            result["metadata"] = self.metadata

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Question":
        """Create question from dictionary representation."""
        # Remove conditional field if present (not serializable)
        data = data.copy()
        data.pop("conditional", None)

        # Support both 'type' and 'question_type' for backward compatibility
        question_type_value = data.get("type") or data.get("question_type", "text")

        return cls(
            id=data["id"],
            text=data["text"],
            question_type=QuestionType(question_type_value),
            required=data.get("required", True),
            help_text=data.get("help_text"),
            placeholder=data.get("placeholder"),
            default_value=data.get("default_value"),
            validation_rules=data.get("validation_rules"),
            options=data.get("options"),
            min_value=data.get("min_value"),
            max_value=data.get("max_value"),
            order=data.get("order", 0),
            metadata=data.get("metadata"),
        )

    def validate_answer(self, answer: Any) -> tuple[bool, Optional[str]]:
        """
        Validate an answer against this question's rules.

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Required check
        if self.required and (answer is None or answer == ""):
            return False, "This question requires an answer"

        # Type-specific validation
        if self.question_type == QuestionType.CHOICE:
            if answer not in self.options:
                return False, f"Answer must be one of: {', '.join(self.options)}"

        elif self.question_type == QuestionType.MULTICHOICE:
            if not isinstance(answer, list):
                return False, "Answer must be a list of choices"
            invalid = [a for a in answer if a not in self.options]
            if invalid:
                return False, f"Invalid choices: {', '.join(invalid)}"

        elif self.question_type in (QuestionType.RATING, QuestionType.SCALE):
            try:
                num_answer = int(answer)
                if num_answer < self.min_value or num_answer > self.max_value:
                    return False, f"Answer must be between {self.min_value} and {self.max_value}"
            except (ValueError, TypeError):
                return (
                    False,
                    f"Answer must be a number between {self.min_value} and {self.max_value}",
                )

        elif self.question_type == QuestionType.BOOLEAN:
            if answer not in [True, False, "yes", "no", "y", "n", "true", "false"]:
                return False, "Answer must be yes/no"

        # Custom validation rules
        if self.validation_rules:
            min_length = self.validation_rules.get("min_length")
            if min_length and len(str(answer)) < min_length:
                return False, f"Answer must be at least {min_length} characters"

            max_length = self.validation_rules.get("max_length")
            if max_length and len(str(answer)) > max_length:
                return False, f"Answer must be at most {max_length} characters"

            pattern = self.validation_rules.get("pattern")
            if pattern:
                import re

                if not re.match(pattern, str(answer)):
                    return False, "Answer format is invalid"

        return True, None

    def should_ask(self, context: Dict[str, Any]) -> bool:
        """
        Determine if this question should be asked based on conditional logic.

        Args:
            context: Dictionary of previous answers and other context

        Returns:
            True if question should be asked, False otherwise
        """
        if self.conditional is None:
            return True
        return self.conditional(context)


@dataclass
class QuestionConfig:
    """
    Configuration for customizing questions.

    Attributes:
        custom_questions: List of custom questions to use instead of defaults
        skip_questions: IDs of default questions to skip
        additional_questions: Questions to add to the default set
        question_order: Custom ordering of question IDs
    """

    custom_questions: Optional[List[Question]] = None
    skip_questions: Optional[List[str]] = None
    additional_questions: Optional[List[Question]] = None
    question_order: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary for serialization."""
        result = {}
        if self.custom_questions:
            result["custom_questions"] = [q.to_dict() for q in self.custom_questions]
        if self.skip_questions:
            result["skip_questions"] = self.skip_questions
        if self.additional_questions:
            result["additional_questions"] = [q.to_dict() for q in self.additional_questions]
        if self.question_order:
            result["question_order"] = self.question_order
        return result

    @classmethod
    def from_dict(cls, data) -> "QuestionConfig":
        """Create config from dictionary representation.

        Supports both dict format and list format (legacy):
        - Dict: {"custom_questions": [...], "skip_questions": [...]}
        - List: [{"id": "q1", "text": "Q1", "type": "text"}]
        """
        # Handle legacy format where questions is just a list
        if isinstance(data, list):
            return cls(
                custom_questions=[Question.from_dict(q) for q in data] or None,
            )

        # Handle full dict format
        return cls(
            custom_questions=[Question.from_dict(q) for q in data.get("custom_questions", [])]
            or None,
            skip_questions=data.get("skip_questions"),
            additional_questions=[
                Question.from_dict(q) for q in data.get("additional_questions", [])
            ]
            or None,
            question_order=data.get("question_order"),
        )


@dataclass
class QuestionSet:
    """
    A complete set of questions for a reflection session.

    Attributes:
        name: Name of the question set
        description: Description of the question set
        questions: List of questions in the set
        version: Version of the question set
        metadata: Additional metadata
    """

    name: str
    questions: List[Question]
    description: Optional[str] = None
    version: str = "1.0"
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Sort questions by order."""
        self.questions.sort(key=lambda q: q.order)

    def to_dict(self) -> Dict[str, Any]:
        """Convert question set to dictionary for serialization."""
        result = {
            "name": self.name,
            "questions": [q.to_dict() for q in self.questions],
            "version": self.version,
        }
        if self.description:
            result["description"] = self.description
        if self.metadata:
            result["metadata"] = self.metadata
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QuestionSet":
        """Create question set from dictionary representation."""
        return cls(
            name=data["name"],
            questions=[Question.from_dict(q) for q in data["questions"]],
            description=data.get("description"),
            version=data.get("version", "1.0"),
            metadata=data.get("metadata"),
        )

    def get_question_by_id(self, question_id: str) -> Optional[Question]:
        """Get a question by its ID."""
        for question in self.questions:
            if question.id == question_id:
                return question
        return None

    def get_questions_for_context(self, context: Dict[str, Any]) -> List[Question]:
        """
        Get questions that should be asked based on context.

        Filters out questions based on conditional logic.
        """
        return [q for q in self.questions if q.should_ask(context)]

    def validate_all_answers(self, answers: Dict[str, Any]) -> Dict[str, Optional[str]]:
        """
        Validate all answers against their questions.

        Returns:
            Dictionary mapping question IDs to error messages (None if valid)
        """
        errors = {}
        for question in self.questions:
            answer = answers.get(question.id)
            is_valid, error = question.validate_answer(answer)
            errors[question.id] = error if not is_valid else None
        return errors


def create_default_question_set() -> QuestionSet:
    """
    Create the default question set for commit reflections.

    These are the 10 core questions for tracking development experience and AI collaboration.
    """
    return QuestionSet(
        name="default",
        description="Default commit reflection questions",
        version="2.0",
        questions=[
            Question(
                id="work_type",
                text="What kind of work does this commit primarily represent?",
                question_type=QuestionType.CHOICE,
                required=True,
                options=[
                    "New Feature",
                    "Bug fixing",
                    "Refactor",
                    "Tests",
                    "Docs",
                    "DevOps/infra/tooling",
                    "Other",
                ],
                help_text="Select the category that best describes this commit",
                order=1,
            ),
            Question(
                id="difficulty",
                text="How difficult was this work for you?",
                question_type=QuestionType.CHOICE,
                required=True,
                options=["Easy", "Moderate", "Hard", "Very Hard"],
                help_text="Assess the difficulty level of this work",
                order=2,
            ),
            Question(
                id="ai_effectiveness",
                text="How effective was AI collaboration on this commit?",
                question_type=QuestionType.CHOICE,
                required=True,
                options=["Very Low", "Low", "Medium", "High", "Very High"],
                help_text="Rate how helpful AI was in completing this work",
                order=3,
            ),
            Question(
                id="who_drove",
                text='For this commit, who did most of the "driving"?',
                question_type=QuestionType.CHOICE,
                required=True,
                options=["Mostly me", "Shared evenly", "Mostly AI"],
                help_text="Who was primarily directing the work?",
                order=4,
            ),
            Question(
                id="confidence",
                text="How confident are you that this commit is correct and safe to merge?",
                question_type=QuestionType.CHOICE,
                required=True,
                options=["Very Low", "Low", "High", "Very High"],
                help_text="Your confidence in the correctness and safety of these changes",
                order=5,
            ),
            Question(
                id="experience",
                text="How did this work feel?",
                question_type=QuestionType.MULTILINE,
                required=True,
                help_text="Describe your experience (e.g. Smooth, Frustrating, Lots of back-and-forth, Flow state)",
                placeholder="e.g., Smooth, Frustrating, Lots of back-and-forth, Flow state",
                order=6,
            ),
            Question(
                id="blockers_and_friction",
                text="Did you hit any blockers or friction on this commit? If yes, what best describes them?",
                question_type=QuestionType.MULTICHOICE,
                required=False,
                options=[
                    "AI misunderstanding",
                    "Missing requirements context",
                    "Tools/environment/infra issues",
                    "Codebase complexity/architecture confusion",
                    "My own clarity/changing direction",
                    "Other",
                ],
                help_text="Select all that apply (or skip if no blockers)",
                order=7,
                metadata={"allow_other_text": True},
            ),
            Question(
                id="learning",
                text="Did you learn something worth remembering from this commit? If yes, what?",
                question_type=QuestionType.MULTILINE,
                required=False,
                help_text="Share any insights or knowledge gained",
                placeholder="I learned that...",
                order=8,
            ),
            Question(
                id="agent_feedback",
                text="For this commit, what should the agent do differently next time, if anything?",
                question_type=QuestionType.MULTILINE,
                required=False,
                help_text="e.g., Ask clarifying questions; Be concise; Propose concrete code changes; Be opinionated; Slow down and verify assumptions; Surface more context like files/tests/docs automatically; Other",
                placeholder="e.g., Ask clarifying questions, Be concise, Propose concrete code changes...",
                order=9,
            ),
            Question(
                id="outcome",
                text="How would you describe the outcome of this commit?",
                question_type=QuestionType.CHOICE,
                required=True,
                options=[
                    "Completed what I intended",
                    "Partial progress",
                    "Unblocks something else",
                    "Spike",
                    "Fixed fallout from earlier changes",
                    "Other",
                ],
                help_text="What did this commit accomplish?",
                order=10,
                metadata={"allow_other_text": True},
            ),
        ],
    )
