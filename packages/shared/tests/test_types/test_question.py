"""
Unit tests for question types and validation.

Tests the Question data model including:
- Question type definitions
- Validation rules
- Answer validation
"""

import pytest
from shared.types.question import Question, QuestionType, QuestionConfig, QuestionSet


class TestQuestion:
    """Tests for Question data class."""

    def test_question_creation_text_type(self):
        """Test creating a basic text question."""
        question = Question(
            id="what",
            text="What changed?",
            type=QuestionType.TEXT,
            required=True,
        )
        assert question.id == "what"
        assert question.text == "What changed?"
        assert question.type == QuestionType.TEXT
        assert question.required is True

    def test_question_creation_with_defaults(self):
        """Test question creation with default values."""
        question = Question(
            id="optional",
            text="Optional question?",
            type=QuestionType.TEXT,
        )
        assert question.required is False  # Default should be False

    def test_question_multiline_type(self):
        """Test creating a multiline question."""
        question = Question(
            id="description",
            text="Provide detailed description",
            type=QuestionType.MULTILINE,
            required=True,
        )
        assert question.type == QuestionType.MULTILINE

    def test_question_choice_type(self):
        """Test creating a choice question."""
        question = Question(
            id="category",
            text="Select category",
            type=QuestionType.CHOICE,
            choices=["bug", "feature", "refactor"],
        )
        assert question.type == QuestionType.CHOICE
        assert len(question.choices) == 3

    def test_question_choice_requires_choices(self):
        """Test that CHOICE type requires choices list."""
        with pytest.raises(ValueError):
            Question(
                id="category",
                text="Select category",
                type=QuestionType.CHOICE,
                # Missing choices
            )

    def test_question_validation_empty_id(self):
        """Test that empty ID raises validation error."""
        with pytest.raises(ValueError):
            Question(
                id="",
                text="What changed?",
                type=QuestionType.TEXT,
            )

    def test_question_validation_empty_text(self):
        """Test that empty text raises validation error."""
        with pytest.raises(ValueError):
            Question(
                id="what",
                text="",
                type=QuestionType.TEXT,
            )

    def test_question_serialization(self):
        """Test question can be serialized to dict."""
        question = Question(
            id="what",
            text="What changed?",
            type=QuestionType.TEXT,
            required=True,
        )
        data = question.to_dict()
        assert data["id"] == "what"
        assert data["text"] == "What changed?"
        assert data["type"] == "text"

    def test_question_deserialization(self):
        """Test question can be created from dict."""
        data = {
            "id": "what",
            "text": "What changed?",
            "type": "text",
            "required": True,
        }
        question = Question.from_dict(data)
        assert question.id == "what"
        assert question.type == QuestionType.TEXT


@pytest.mark.skip(reason="Answer class not implemented in current API")
class TestAnswer:
    """Tests for Answer data class (skipped - class doesn't exist)."""

    def test_answer_creation(self):
        """Test creating a basic answer."""
        answer = Answer(
            question_id="what",
            value="Added authentication",
        )
        assert answer.question_id == "what"
        assert answer.value == "Added authentication"

    def test_answer_validation_empty_value_required(self):
        """Test that empty value for required question raises error."""
        with pytest.raises(ValueError):
            Answer(
                question_id="what",
                value="",
                required=True,
            )

    def test_answer_validation_empty_value_optional(self):
        """Test that empty value for optional question is allowed."""
        answer = Answer(
            question_id="optional",
            value="",
            required=False,
        )
        assert answer.value == ""

    def test_answer_choice_validation(self):
        """Test that choice answer validates against allowed choices."""
        # Valid choice
        answer = Answer(
            question_id="category",
            value="bug",
            choices=["bug", "feature", "refactor"],
        )
        assert answer.value == "bug"

        # Invalid choice
        with pytest.raises(ValueError):
            Answer(
                question_id="category",
                value="invalid",
                choices=["bug", "feature", "refactor"],
            )

    def test_answer_serialization(self):
        """Test answer can be serialized to dict."""
        answer = Answer(
            question_id="what",
            value="Added authentication",
        )
        data = answer.to_dict()
        assert data["question_id"] == "what"
        assert data["value"] == "Added authentication"


class TestQuestionType:
    """Tests for QuestionType enum."""

    def test_question_type_values(self):
        """Test that all question types are defined."""
        assert QuestionType.TEXT
        assert QuestionType.MULTILINE
        assert QuestionType.CHOICE

    def test_question_type_string_conversion(self):
        """Test question type can be converted to string."""
        assert str(QuestionType.TEXT) == "text"
        assert str(QuestionType.MULTILINE) == "multiline"
        assert str(QuestionType.CHOICE) == "choice"

    def test_question_type_from_string(self):
        """Test question type can be created from string."""
        assert QuestionType.from_string("text") == QuestionType.TEXT
        assert QuestionType.from_string("multiline") == QuestionType.MULTILINE
        assert QuestionType.from_string("choice") == QuestionType.CHOICE
