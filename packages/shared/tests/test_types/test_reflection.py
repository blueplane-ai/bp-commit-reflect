"""
Unit tests for reflection types and validation.

Tests the core Reflection data model including:
- Data validation and type checking
- Serialization and deserialization
- Field requirements and constraints
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4, UUID
from shared.types.reflection import Reflection, CommitContext, ReflectionAnswer, SessionMetadata


class TestCommitContext:
    """Tests for CommitContext data class."""

    def test_commit_context_creation(self):
        """Test basic commit context creation with all required fields."""
        context = CommitContext(
            commit_hash="abc123def456",
            commit_message="feat: add user authentication",
            branch="feature/auth",
            author_name="Test Author",
            author_email="test@example.com",
            timestamp=datetime.now(timezone.utc),
        )
        assert context.commit_hash == "abc123def456"
        assert context.author_name == "Test Author"
        assert context.author_email == "test@example.com"
        assert context.branch == "feature/auth"
        assert context.commit_message == "feat: add user authentication"

    def test_commit_context_with_stats(self):
        """Test commit context with optional statistics fields."""
        context = CommitContext(
            commit_hash="abc123",
            commit_message="test commit",
            branch="main",
            author_name="Test",
            author_email="test@example.com",
            timestamp=datetime.now(timezone.utc),
            files_changed=5,
            insertions=100,
            deletions=50,
            changed_files=["file1.py", "file2.py"],
        )
        assert context.files_changed == 5
        assert context.insertions == 100
        assert context.deletions == 50
        assert len(context.changed_files) == 2

    def test_commit_context_with_defaults(self):
        """Test commit context uses default values for optional fields."""
        context = CommitContext(
            commit_hash="abc123",
            commit_message="test",
            branch="main",
            author_name="Test",
            author_email="test@example.com",
            timestamp=datetime.now(timezone.utc),
        )
        assert context.files_changed == 0
        assert context.insertions == 0
        assert context.deletions == 0
        assert context.changed_files == []

    def test_commit_context_serialization(self):
        """Test commit context can be serialized to dict."""
        timestamp = datetime.now(timezone.utc)
        context = CommitContext(
            commit_hash="abc123",
            commit_message="test",
            branch="main",
            author_name="Test",
            author_email="test@example.com",
            timestamp=timestamp,
        )
        data = context.to_dict()
        assert isinstance(data, dict)
        assert data["commit_hash"] == "abc123"
        assert data["author_name"] == "Test"
        assert data["author_email"] == "test@example.com"
        assert data["timestamp"] == timestamp.isoformat()

    def test_commit_context_deserialization(self):
        """Test commit context can be created from dict."""
        data = {
            "commit_hash": "abc123",
            "commit_message": "test commit",
            "branch": "main",
            "author_name": "Test",
            "author_email": "test@example.com",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "files_changed": 3,
            "insertions": 50,
            "deletions": 20,
            "changed_files": ["file1.py"],
        }
        context = CommitContext.from_dict(data)
        assert context.commit_hash == "abc123"
        assert context.author_name == "Test"
        assert context.files_changed == 3


class TestReflectionAnswer:
    """Tests for ReflectionAnswer data class."""

    def test_answer_creation(self):
        """Test creating a reflection answer."""
        answer = ReflectionAnswer(
            question_id="what",
            question_text="What changed?",
            answer="Added authentication",
            answered_at=datetime.now(timezone.utc),
        )
        assert answer.question_id == "what"
        assert answer.answer == "Added authentication"
        assert answer.metadata is None

    def test_answer_with_metadata(self):
        """Test answer with optional metadata."""
        answer = ReflectionAnswer(
            question_id="what",
            question_text="What changed?",
            answer="Added feature",
            answered_at=datetime.now(timezone.utc),
            metadata={"time_to_answer": 30},
        )
        assert answer.metadata["time_to_answer"] == 30

    def test_answer_serialization(self):
        """Test answer can be serialized to dict."""
        timestamp = datetime.now(timezone.utc)
        answer = ReflectionAnswer(
            question_id="what",
            question_text="What changed?",
            answer="Test",
            answered_at=timestamp,
        )
        data = answer.to_dict()
        assert data["question_id"] == "what"
        assert data["answer"] == "Test"
        assert data["answered_at"] == timestamp.isoformat()

    def test_answer_deserialization(self):
        """Test answer can be created from dict."""
        data = {
            "question_id": "what",
            "question_text": "What changed?",
            "answer": "Test",
            "answered_at": datetime.now(timezone.utc).isoformat(),
        }
        answer = ReflectionAnswer.from_dict(data)
        assert answer.question_id == "what"
        assert answer.answer == "Test"


class TestReflection:
    """Tests for Reflection data class."""

    def test_reflection_creation(self, sample_reflection_object):
        """Test creating a complete reflection."""
        reflection = sample_reflection_object
        assert isinstance(reflection.id, UUID)
        assert len(reflection.answers) > 0
        assert isinstance(reflection.commit_context, CommitContext)
        assert isinstance(reflection.session_metadata, SessionMetadata)

    def test_reflection_with_minimal_data(self):
        """Test reflection with minimal required fields."""
        reflection = Reflection(
            id=uuid4(),
            answers=[
                ReflectionAnswer(
                    question_id="what",
                    question_text="What changed?",
                    answer="Added feature",
                    answered_at=datetime.now(timezone.utc),
                )
            ],
            commit_context=CommitContext(
                commit_hash="abc123",
                commit_message="test",
                branch="main",
                author_name="Test",
                author_email="test@example.com",
                timestamp=datetime.now(timezone.utc),
            ),
            session_metadata=SessionMetadata(
                session_id=uuid4(),
                started_at=datetime.now(timezone.utc),
            ),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        assert reflection.id is not None
        assert len(reflection.answers) == 1

    def test_reflection_serialization(self, sample_reflection_object):
        """Test reflection can be serialized to dict."""
        reflection = sample_reflection_object
        data = reflection.to_dict()
        assert isinstance(data, dict)
        assert "id" in data
        assert "answers" in data
        assert "commit_context" in data
        assert "session_metadata" in data
        assert isinstance(data["answers"], list)

    def test_reflection_deserialization(self, sample_reflection_object):
        """Test reflection can be created from dict."""
        reflection = sample_reflection_object
        data = reflection.to_dict()

        # Recreate from dict
        restored = Reflection.from_dict(data)
        assert restored.id == reflection.id
        assert len(restored.answers) == len(reflection.answers)
        assert restored.commit_context.commit_hash == reflection.commit_context.commit_hash

    def test_reflection_get_answer_by_question_id(self, sample_reflection_object):
        """Test retrieving answer by question ID."""
        reflection = sample_reflection_object
        answer = reflection.get_answer_by_question_id("ai_synergy")
        assert answer is not None
        assert answer.question_id == "ai_synergy"

        # Test non-existent question
        missing = reflection.get_answer_by_question_id("nonexistent")
        assert missing is None

    def test_reflection_is_complete(self, sample_reflection_object):
        """Test checking if reflection has all expected answers."""
        reflection = sample_reflection_object
        assert reflection.is_complete(3) is True
        assert reflection.is_complete(10) is False

    def test_reflection_summary(self, sample_reflection_object):
        """Test generating reflection summary."""
        reflection = sample_reflection_object
        summary = reflection.summary()
        assert "abc123de" in summary  # First 8 chars of commit hash
        assert "feature/auth" in summary
        assert "3 answers" in summary

    def test_reflection_equality(self, sample_reflection_object):
        """Test two reflections with same ID are considered equal (by ID)."""
        reflection1 = sample_reflection_object
        data = reflection1.to_dict()
        reflection2 = Reflection.from_dict(data)
        assert reflection1.id == reflection2.id


class TestSessionMetadata:
    """Tests for SessionMetadata data class."""

    def test_session_metadata_creation(self):
        """Test creating session metadata."""
        session_id = uuid4()
        metadata = SessionMetadata(
            session_id=session_id,
            started_at=datetime.now(timezone.utc),
        )
        assert metadata.session_id == session_id
        assert metadata.completed_at is None
        assert metadata.interrupted is False

    def test_session_metadata_with_completion(self):
        """Test session metadata with completion time."""
        started = datetime.now(timezone.utc)
        completed = datetime.now(timezone.utc)
        metadata = SessionMetadata(
            session_id=uuid4(),
            started_at=started,
            completed_at=completed,
            project_name="test-project",
        )
        assert metadata.completed_at == completed
        assert metadata.project_name == "test-project"

    def test_session_metadata_string_uuid_conversion(self):
        """Test that string UUIDs are converted to UUID objects."""
        uuid_str = str(uuid4())
        metadata = SessionMetadata(
            session_id=uuid_str,
            started_at=datetime.now(timezone.utc),
        )
        assert isinstance(metadata.session_id, UUID)
        assert str(metadata.session_id) == uuid_str

    def test_session_metadata_serialization(self):
        """Test session metadata can be serialized to dict."""
        session_id = uuid4()
        started = datetime.now(timezone.utc)
        metadata = SessionMetadata(
            session_id=session_id,
            started_at=started,
            project_name="test",
            tool_version="0.1.0",
        )
        data = metadata.to_dict()
        assert data["session_id"] == str(session_id)
        assert data["started_at"] == started.isoformat()
        assert data["project_name"] == "test"

    def test_session_metadata_deserialization(self):
        """Test session metadata can be created from dict."""
        data = {
            "session_id": str(uuid4()),
            "started_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "project_name": "test",
            "tool_version": "0.1.0",
            "environment": "cli",
            "interrupted": False,
        }
        metadata = SessionMetadata.from_dict(data)
        assert str(metadata.session_id) == data["session_id"]
        assert metadata.project_name == "test"
        assert metadata.interrupted is False
