"""
Core reflection data model for the Commit Reflection System.

This module defines the primary data structures for storing and
representing commit reflections, including answers, context, and metadata.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4


@dataclass
class ReflectionAnswer:
    """
    A single answer to a reflection question.

    Attributes:
        question_id: Unique identifier of the question being answered
        question_text: The full text of the question as presented
        answer: The user's response to the question
        answered_at: Timestamp when the answer was provided
        metadata: Optional metadata about the answer (e.g., time to answer)
    """

    question_id: str
    question_text: str
    answer: str
    answered_at: datetime
    metadata: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert answer to dictionary for serialization."""
        result = {
            "question_id": self.question_id,
            "question_text": self.question_text,
            "answer": self.answer,
            "answered_at": self.answered_at.isoformat(),
        }
        if self.metadata:
            result["metadata"] = self.metadata
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReflectionAnswer":
        """Create answer from dictionary representation."""
        return cls(
            question_id=data["question_id"],
            question_text=data["question_text"],
            answer=data["answer"],
            answered_at=datetime.fromisoformat(data["answered_at"]),
            metadata=data.get("metadata"),
        )


@dataclass
class CommitContext:
    """
    Context information about the commit being reflected upon.

    Attributes:
        commit_hash: The git commit hash
        commit_message: The original commit message
        branch: The branch name where the commit was made
        author_name: Name of the commit author
        author_email: Email of the commit author
        timestamp: When the commit was created
        files_changed: Number of files changed in the commit
        insertions: Number of line insertions
        deletions: Number of line deletions
        changed_files: List of file paths that were changed
    """

    commit_hash: str
    commit_message: str
    branch: str
    author_name: str
    author_email: str
    timestamp: datetime
    files_changed: int = 0
    insertions: int = 0
    deletions: int = 0
    changed_files: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert context to dictionary for serialization."""
        return {
            "commit_hash": self.commit_hash,
            "commit_message": self.commit_message,
            "branch": self.branch,
            "author_name": self.author_name,
            "author_email": self.author_email,
            "timestamp": self.timestamp.isoformat(),
            "files_changed": self.files_changed,
            "insertions": self.insertions,
            "deletions": self.deletions,
            "changed_files": self.changed_files,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CommitContext":
        """Create context from dictionary representation."""
        return cls(
            commit_hash=data["commit_hash"],
            commit_message=data["commit_message"],
            branch=data["branch"],
            author_name=data["author_name"],
            author_email=data["author_email"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            files_changed=data.get("files_changed", 0),
            insertions=data.get("insertions", 0),
            deletions=data.get("deletions", 0),
            changed_files=data.get("changed_files", []),
        )


@dataclass
class SessionMetadata:
    """
    Metadata about the reflection session itself.

    Attributes:
        session_id: Unique identifier for this reflection session
        started_at: When the reflection session began
        completed_at: When the reflection session completed (None if incomplete)
        project_name: Name of the project being reflected upon
        tool_version: Version of the reflection tool used
        environment: Environment info (e.g., IDE, terminal, MCP)
        interrupted: Whether the session was interrupted before completion
        additional_context: Any additional context provided
    """

    session_id: UUID
    started_at: datetime
    completed_at: Optional[datetime] = None
    project_name: Optional[str] = None
    tool_version: Optional[str] = None
    environment: Optional[str] = None
    interrupted: bool = False
    additional_context: Optional[dict[str, Any]] = None

    def __post_init__(self) -> None:
        """Ensure session_id is a UUID."""
        if isinstance(self.session_id, str):
            self.session_id = UUID(self.session_id)

    def to_dict(self) -> dict[str, Any]:
        """Convert metadata to dictionary for serialization."""
        result = {
            "session_id": str(self.session_id),
            "started_at": self.started_at.isoformat(),
            "interrupted": self.interrupted,
        }
        if self.completed_at:
            result["completed_at"] = self.completed_at.isoformat()
        if self.project_name:
            result["project_name"] = self.project_name
        if self.tool_version:
            result["tool_version"] = self.tool_version
        if self.environment:
            result["environment"] = self.environment
        if self.additional_context:
            result["additional_context"] = self.additional_context
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionMetadata":
        """Create metadata from dictionary representation."""
        return cls(
            session_id=UUID(data["session_id"]),
            started_at=datetime.fromisoformat(data["started_at"]),
            completed_at=(
                datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None
            ),
            project_name=data.get("project_name"),
            tool_version=data.get("tool_version"),
            environment=data.get("environment"),
            interrupted=data.get("interrupted", False),
            additional_context=data.get("additional_context"),
        )


@dataclass
class Reflection:
    """
    A complete reflection on a git commit.

    This is the primary data structure that combines all aspects of a
    reflection session including answers, context, and metadata.

    Attributes:
        id: Unique identifier for the reflection
        answers: List of answers to reflection questions
        commit_context: Information about the commit being reflected upon
        session_metadata: Information about the reflection session
        created_at: When the reflection was created
        updated_at: When the reflection was last updated
    """

    id: UUID
    answers: list[ReflectionAnswer]
    commit_context: CommitContext
    session_metadata: SessionMetadata
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        """Initialize defaults and ensure types."""
        if self.id is None:
            self.id = uuid4()
        elif isinstance(self.id, str):
            self.id = UUID(self.id)

        if self.created_at is None:
            self.created_at = datetime.now()

        if self.updated_at is None:
            self.updated_at = self.created_at

    def to_dict(self) -> dict[str, Any]:
        """Convert reflection to dictionary for serialization."""
        return {
            "id": str(self.id),
            "answers": [answer.to_dict() for answer in self.answers],
            "commit_context": self.commit_context.to_dict(),
            "session_metadata": self.session_metadata.to_dict(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Reflection":
        """Create reflection from dictionary representation."""
        return cls(
            id=UUID(data["id"]),
            answers=[ReflectionAnswer.from_dict(a) for a in data["answers"]],
            commit_context=CommitContext.from_dict(data["commit_context"]),
            session_metadata=SessionMetadata.from_dict(data["session_metadata"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )

    def get_answer_by_question_id(self, question_id: str) -> Optional[ReflectionAnswer]:
        """Get a specific answer by question ID."""
        for answer in self.answers:
            if answer.question_id == question_id:
                return answer
        return None

    def is_complete(self, expected_question_count: int) -> bool:
        """Check if the reflection has all expected answers."""
        return len(self.answers) >= expected_question_count

    def summary(self) -> str:
        """Generate a brief summary of the reflection."""
        return (
            f"Reflection for commit {self.commit_context.commit_hash[:8]} "
            f"on {self.commit_context.branch} branch "
            f"({len(self.answers)} answers)"
        )
