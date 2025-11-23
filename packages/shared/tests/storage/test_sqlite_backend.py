"""
Tests for SQLite storage backend.

Tests the SQLite storage implementation including schema initialization,
migrations, save/retrieve operations, and querying.
"""

import pytest
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from storage.sqlite import SQLiteStorage
from types.reflection import (
    Reflection,
    ReflectionAnswer,
    CommitContext,
    SessionMetadata,
)
from types.storage import StorageResult, QueryOptions, SortOrder


@pytest.mark.storage
class TestSQLiteStorage:
    """Tests for SQLiteStorage backend."""

    def test_sqlite_storage_initialization(self, temp_sqlite_db):
        """Test SQLite storage initialization creates database."""
        storage = SQLiteStorage({"path": str(temp_sqlite_db)})
        
        result = storage.initialize()
        assert result.success is True
        assert storage.is_initialized()
        assert temp_sqlite_db.exists()

    def test_sqlite_storage_creates_schema(self, temp_sqlite_db):
        """Test that schema is created on initialization."""
        storage = SQLiteStorage({"path": str(temp_sqlite_db)})
        storage.initialize()
        
        # Check that schema version table exists
        import sqlite3
        conn = sqlite3.connect(str(temp_sqlite_db))
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
        )
        assert cursor.fetchone() is not None
        conn.close()

    def test_sqlite_storage_save_reflection(self, temp_sqlite_db, sample_reflection_object):
        """Test saving a reflection."""
        storage = SQLiteStorage({"path": str(temp_sqlite_db)})
        storage.initialize()
        
        result = storage.save_reflection(sample_reflection_object)
        assert result.success is True

    def test_sqlite_storage_get_reflection(self, temp_sqlite_db, sample_reflection_object):
        """Test retrieving a reflection by ID."""
        storage = SQLiteStorage({"path": str(temp_sqlite_db)})
        storage.initialize()
        
        # Save reflection
        storage.save_reflection(sample_reflection_object)
        
        # Retrieve it
        retrieved = storage.get_reflection(sample_reflection_object.id)
        assert retrieved is not None
        assert retrieved.id == sample_reflection_object.id
        assert len(retrieved.answers) == len(sample_reflection_object.answers)

    def test_sqlite_storage_get_nonexistent_reflection(self, temp_sqlite_db):
        """Test retrieving non-existent reflection returns None."""
        storage = SQLiteStorage({"path": str(temp_sqlite_db)})
        storage.initialize()
        
        result = storage.get_reflection(uuid4())
        assert result is None

    def test_sqlite_storage_update_reflection(self, temp_sqlite_db, sample_reflection_object):
        """Test updating an existing reflection."""
        storage = SQLiteStorage({"path": str(temp_sqlite_db)})
        storage.initialize()
        
        # Save initial reflection
        storage.save_reflection(sample_reflection_object)
        
        # Update with new answer
        sample_reflection_object.answers.append(
            ReflectionAnswer(
                question_id="new_question",
                question_text="New question?",
                answer="New answer",
                answered_at=datetime.now(timezone.utc),
            )
        )
        sample_reflection_object.updated_at = datetime.now(timezone.utc)
        
        result = storage.save_reflection(sample_reflection_object)
        assert result.success is True
        
        # Verify update
        retrieved = storage.get_reflection(sample_reflection_object.id)
        assert len(retrieved.answers) == len(sample_reflection_object.answers)

    def test_sqlite_storage_query_reflections(self, temp_sqlite_db):
        """Test querying reflections with options."""
        storage = SQLiteStorage({"path": str(temp_sqlite_db)})
        storage.initialize()
        
        # Create multiple reflections
        for i in range(5):
            reflection = Reflection(
                id=uuid4(),
                answers=[
                    ReflectionAnswer(
                        question_id="what",
                        question_text="What changed?",
                        answer=f"Change {i}",
                        answered_at=datetime.now(timezone.utc),
                    )
                ],
                commit_context=CommitContext(
                    commit_hash=f"hash{i}",
                    commit_message=f"Message {i}",
                    branch="main",
                    author_name="Test Author",
                    author_email="test@example.com",
                    timestamp=datetime.now(timezone.utc),
                ),
                session_metadata=SessionMetadata(
                    session_id=uuid4(),
                    started_at=datetime.now(timezone.utc),
                    project_name=f"project{i % 2}",  # Alternating projects
                ),
            )
            storage.save_reflection(reflection)
        
        # Query all reflections
        options = QueryOptions(limit=10)
        reflections = storage.query_reflections(options)
        assert len(reflections) == 5

    def test_sqlite_storage_query_with_project_filter(self, temp_sqlite_db):
        """Test querying with project filter."""
        storage = SQLiteStorage({"path": str(temp_sqlite_db)})
        storage.initialize()
        
        # Create reflections for different projects
        for project in ["project1", "project2", "project1"]:
            reflection = Reflection(
                id=uuid4(),
                answers=[
                    ReflectionAnswer(
                        question_id="what",
                        question_text="What changed?",
                        answer="Change",
                        answered_at=datetime.now(timezone.utc),
                    )
                ],
                commit_context=CommitContext(
                    commit_hash=uuid4().hex[:8],
                    commit_message="Test",
                    branch="main",
                    author_name="Test",
                    author_email="test@example.com",
                    timestamp=datetime.now(timezone.utc),
                ),
                session_metadata=SessionMetadata(
                    session_id=uuid4(),
                    started_at=datetime.now(timezone.utc),
                    project_name=project,
                ),
            )
            storage.save_reflection(reflection)
        
        # Query by project
        options = QueryOptions(project_name="project1")
        reflections = storage.query_reflections(options)
        assert len(reflections) == 2
        assert all(r.session_metadata.project_name == "project1" for r in reflections)

    def test_sqlite_storage_query_with_limit(self, temp_sqlite_db):
        """Test querying with limit."""
        storage = SQLiteStorage({"path": str(temp_sqlite_db)})
        storage.initialize()
        
        # Create multiple reflections
        for i in range(10):
            reflection = Reflection(
                id=uuid4(),
                answers=[
                    ReflectionAnswer(
                        question_id="what",
                        question_text="What changed?",
                        answer=f"Change {i}",
                        answered_at=datetime.now(timezone.utc),
                    )
                ],
                commit_context=CommitContext(
                    commit_hash=f"hash{i}",
                    commit_message="Test",
                    branch="main",
                    author_name="Test",
                    author_email="test@example.com",
                    timestamp=datetime.now(timezone.utc),
                ),
                session_metadata=SessionMetadata(
                    session_id=uuid4(),
                    started_at=datetime.now(timezone.utc),
                ),
            )
            storage.save_reflection(reflection)
        
        # Query with limit
        options = QueryOptions(limit=5)
        reflections = storage.query_reflections(options)
        assert len(reflections) == 5

    def test_sqlite_storage_count_reflections(self, temp_sqlite_db):
        """Test counting reflections."""
        storage = SQLiteStorage({"path": str(temp_sqlite_db)})
        storage.initialize()
        
        # Create reflections
        for i in range(7):
            reflection = Reflection(
                id=uuid4(),
                answers=[
                    ReflectionAnswer(
                        question_id="what",
                        question_text="What changed?",
                        answer=f"Change {i}",
                        answered_at=datetime.now(timezone.utc),
                    )
                ],
                commit_context=CommitContext(
                    commit_hash=f"hash{i}",
                    commit_message="Test",
                    branch="main",
                    author_name="Test",
                    author_email="test@example.com",
                    timestamp=datetime.now(timezone.utc),
                ),
                session_metadata=SessionMetadata(
                    session_id=uuid4(),
                    started_at=datetime.now(timezone.utc),
                ),
            )
            storage.save_reflection(reflection)
        
        count = storage.count_reflections()
        assert count == 7

    def test_sqlite_storage_delete_reflection(self, temp_sqlite_db, sample_reflection_object):
        """Test deleting a reflection."""
        storage = SQLiteStorage({"path": str(temp_sqlite_db)})
        storage.initialize()
        
        # Save reflection
        storage.save_reflection(sample_reflection_object)
        
        # Delete it
        result = storage.delete_reflection(sample_reflection_object.id)
        assert result.success is True
        
        # Verify it's gone
        retrieved = storage.get_reflection(sample_reflection_object.id)
        assert retrieved is None

    def test_sqlite_storage_health_check(self, temp_sqlite_db):
        """Test health check."""
        storage = SQLiteStorage({"path": str(temp_sqlite_db)})
        
        # Health check before initialization should fail
        result = storage.health_check()
        assert result.success is False
        
        # Health check after initialization should pass
        storage.initialize()
        result = storage.health_check()
        assert result.success is True

    def test_sqlite_storage_close(self, temp_sqlite_db):
        """Test closing storage backend."""
        storage = SQLiteStorage({"path": str(temp_sqlite_db)})
        storage.initialize()
        
        result = storage.close()
        assert result.success is True
        assert not storage.is_initialized()

    def test_sqlite_storage_validates_reflection(self, temp_sqlite_db):
        """Test that invalid reflections are rejected."""
        storage = SQLiteStorage({"path": str(temp_sqlite_db)})
        storage.initialize()
        
        # Create invalid reflection (missing answers)
        invalid_reflection = Reflection(
            id=uuid4(),
            answers=[],  # Empty answers - invalid
            commit_context=CommitContext(
                commit_hash="abc123",
                commit_message="Test",
                branch="main",
                author_name="Test",
                author_email="test@example.com",
                timestamp=datetime.now(timezone.utc),
            ),
            session_metadata=SessionMetadata(
                session_id=uuid4(),
                started_at=datetime.now(timezone.utc),
            ),
        )
        
        result = storage.save_reflection(invalid_reflection)
        assert result.success is False
        assert "Invalid reflection" in result.message
