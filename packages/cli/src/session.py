"""
Reflection session management for the CLI.

This module provides the ReflectionSession class which manages the state
of a reflection session, including question flow, answer collection, and
session completion.
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from shared.types.question import Question, QuestionSet, create_default_question_set
from shared.types.reflection import Reflection, CommitContext, SessionMetadata
from shared.types.config import Config
from .validators import validate_question_answer, ValidationError


@dataclass
class SessionState:
    """
    State of a reflection session.

    Attributes:
        session_id: Unique identifier for this session
        current_question_index: Index of current question (0-based)
        answers: Dictionary mapping question IDs to answers
        started_at: When the session started
        commit_context: Context about the commit being reflected on
        is_complete: Whether all required questions are answered
    """
    session_id: str
    current_question_index: int = 0
    answers: Dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    commit_context: Optional[CommitContext] = None
    is_complete: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "current_question_index": self.current_question_index,
            "answers": self.answers,
            "started_at": self.started_at.isoformat(),
            "is_complete": self.is_complete,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionState":
        """Create state from dictionary."""
        return cls(
            session_id=data["session_id"],
            current_question_index=data.get("current_question_index", 0),
            answers=data.get("answers", {}),
            started_at=datetime.fromisoformat(data["started_at"]),
            is_complete=data.get("is_complete", False),
        )


class ReflectionSession:
    """
    Manages a single reflection session.

    This class handles:
    - Question flow and ordering
    - Answer collection and validation
    - Session state management
    - Session completion detection

    Example:
        >>> session = ReflectionSession(commit_context=context)
        >>> current_q = session.get_current_question()
        >>> session.answer_current_question("My answer")
        >>> if session.is_complete():
        ...     reflection = session.to_reflection()
    """

    def __init__(
        self,
        commit_context: CommitContext,
        question_set: Optional[QuestionSet] = None,
        session_id: Optional[str] = None,
        config: Optional[Config] = None,
    ):
        """
        Initialize a reflection session.

        Args:
            commit_context: Context about the commit being reflected on
            question_set: Questions to ask (defaults to default question set)
            session_id: Session ID (generates new UUID if not provided)
            config: Configuration object (optional)
        """
        self.state = SessionState(
            session_id=session_id or str(uuid.uuid4()),
            commit_context=commit_context,
        )
        self.question_set = question_set or create_default_question_set()
        self.config = config

        # Sort questions by order
        self.questions = sorted(
            self.question_set.questions,
            key=lambda q: q.order
        )

    def get_current_question(self) -> Optional[Question]:
        """
        Get the current question to ask.

        Returns:
            Current Question object, or None if session is complete
        """
        if self.state.is_complete:
            return None

        if self.state.current_question_index >= len(self.questions):
            return None

        return self.questions[self.state.current_question_index]

    def answer_current_question(self, answer: Any) -> tuple[bool, Optional[str]]:
        """
        Answer the current question and advance to next.

        Args:
            answer: The answer to the current question

        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        current_question = self.get_current_question()
        if not current_question:
            return False, "No current question available"

        # Validate the answer
        validated_answer, error = validate_question_answer(current_question, answer)
        if error:
            return False, error

        # Store the answer
        self.state.answers[current_question.id] = validated_answer

        # Move to next question
        self.state.current_question_index += 1

        # Check if session is complete
        if self._check_completion():
            self.state.is_complete = True

        return True, None

    def skip_current_question(self) -> tuple[bool, Optional[str]]:
        """
        Skip the current question (only if it's optional).

        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        current_question = self.get_current_question()
        if not current_question:
            return False, "No current question available"

        if current_question.required:
            return False, f"Question '{current_question.id}' is required and cannot be skipped"

        # Move to next question
        self.state.current_question_index += 1

        # Check if session is complete
        if self._check_completion():
            self.state.is_complete = True

        return True, None

    def go_back(self) -> bool:
        """
        Go back to the previous question.

        Returns:
            True if successful, False if already at first question
        """
        if self.state.current_question_index > 0:
            self.state.current_question_index -= 1
            self.state.is_complete = False
            return True
        return False

    def is_complete(self) -> bool:
        """
        Check if the session is complete.

        Returns:
            True if all required questions have been answered
        """
        return self.state.is_complete

    def _check_completion(self) -> bool:
        """
        Check if all required questions have been answered.

        Returns:
            True if session is complete
        """
        # Session is complete if we've gone through all questions
        if self.state.current_question_index >= len(self.questions):
            # Verify all required questions have answers
            for question in self.questions:
                if question.required and question.id not in self.state.answers:
                    return False
            return True
        return False

    def get_progress(self) -> tuple[int, int]:
        """
        Get progress through the question set.

        Returns:
            Tuple of (current_question_number, total_questions)
        """
        return (self.state.current_question_index + 1, len(self.questions))

    def get_answered_questions(self) -> List[str]:
        """
        Get list of question IDs that have been answered.

        Returns:
            List of question IDs with answers
        """
        return list(self.state.answers.keys())

    def get_answer(self, question_id: str) -> Optional[Any]:
        """
        Get the answer for a specific question.

        Args:
            question_id: ID of the question

        Returns:
            The answer, or None if not answered
        """
        return self.state.answers.get(question_id)

    def to_reflection(self) -> Reflection:
        """
        Convert the completed session to a Reflection object.

        Returns:
            Reflection object ready for storage

        Raises:
            ValueError: If session is not complete
        """
        if not self.is_complete():
            raise ValueError("Cannot create reflection from incomplete session")

        # Create session metadata
        session_metadata = SessionMetadata(
            session_id=uuid.UUID(self.state.session_id),
            started_at=self.state.started_at,
            completed_at=datetime.now(timezone.utc),
            additional_context={
                "question_set_version": self.question_set.version,
            } if hasattr(self.question_set, 'version') else None,
        )

        # Convert answers dict to list of ReflectionAnswer objects
        from shared.types.reflection import ReflectionAnswer
        answer_list = []
        for question in self.question_set.questions:
            if question.id in self.state.answers:
                answer_value = self.state.answers[question.id]
                # Convert answer value to string if it's not already
                answer_str = str(answer_value) if answer_value is not None else ""
                answer_list.append(ReflectionAnswer(
                    question_id=question.id,
                    question_text=question.text,
                    answer=answer_str,
                    answered_at=self.state.started_at,  # We don't track individual answer times
                ))

        # Create the reflection
        now = datetime.now(timezone.utc)
        reflection = Reflection(
            id=uuid.uuid4(),
            commit_context=self.state.commit_context,
            answers=answer_list,
            session_metadata=session_metadata,
            created_at=now,
            updated_at=now,
        )

        return reflection

    def get_state(self) -> SessionState:
        """
        Get the current session state.

        Returns:
            SessionState object
        """
        return self.state

    @classmethod
    def from_state(
        cls,
        state: SessionState,
        commit_context: CommitContext,
        question_set: Optional[QuestionSet] = None,
        config: Optional[Config] = None,
    ) -> "ReflectionSession":
        """
        Restore a session from saved state.

        Args:
            state: Saved session state
            commit_context: Commit context
            question_set: Question set to use
            config: Configuration

        Returns:
            Restored ReflectionSession
        """
        session = cls(
            commit_context=commit_context,
            question_set=question_set,
            session_id=state.session_id,
            config=config,
        )
        session.state = state
        return session
