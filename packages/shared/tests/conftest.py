"""
Shared pytest fixtures for commit-reflect testing infrastructure.

This module provides common fixtures used across all test modules,
including mock commits, storage backends, and test data generators.
"""

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List
from unittest.mock import Mock

import pytest


# ============================================================================
# Mock Commit Fixtures
# ============================================================================


@pytest.fixture
def mock_commit_metadata() -> Dict:
    """
    Basic mock commit metadata for testing.

    Returns a dictionary representing git commit metadata with all
    standard fields populated.
    """
    return {
        "hash": "abc123def456",
        "author": "Test Author <test@example.com>",
        "timestamp": "2024-01-15T10:30:00Z",
        "message": "feat: add user authentication",
        "files_changed": ["src/auth.py", "tests/test_auth.py"],
        "insertions": 150,
        "deletions": 20,
        "branch": "feature/auth",
    }


@pytest.fixture
def mock_commit_with_stats() -> Dict:
    """
    Mock commit with detailed statistics.

    Includes per-file statistics and more detailed commit information.
    """
    return {
        "hash": "def456abc789",
        "author": "Dev Team <dev@example.com>",
        "timestamp": "2024-01-15T14:45:00Z",
        "message": "fix: resolve authentication edge case\n\nFixed issue where users couldn't login with special characters",
        "files_changed": ["src/auth.py", "src/validators.py"],
        "insertions": 45,
        "deletions": 12,
        "branch": "bugfix/auth-special-chars",
        "file_stats": [
            {"file": "src/auth.py", "insertions": 30, "deletions": 8},
            {"file": "src/validators.py", "insertions": 15, "deletions": 4},
        ],
    }


@pytest.fixture
def mock_large_commit() -> Dict:
    """
    Mock commit representing a large refactoring change.

    Useful for testing performance and handling of large commits.
    """
    return {
        "hash": "789abc123def",
        "author": "Senior Dev <senior@example.com>",
        "timestamp": "2024-01-16T09:00:00Z",
        "message": "refactor: restructure authentication module",
        "files_changed": [f"src/auth/module_{i}.py" for i in range(20)],
        "insertions": 850,
        "deletions": 620,
        "branch": "refactor/auth-structure",
    }


# ============================================================================
# Reflection Data Fixtures
# ============================================================================


@pytest.fixture
def sample_reflection() -> Dict:
    """
    Sample complete reflection with all required fields.

    Represents a fully completed reflection session with answers
    to all reflection questions.
    """
    return {
        "commit_hash": "abc123def456",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "what_changed": "Added JWT-based authentication system with token refresh",
        "why_changed": "Users needed secure session management without server-side state",
        "how_changed": "Implemented JWT tokens with RS256 signing, 1-hour expiry, 7-day refresh",
        "challenges": "Handled edge cases for concurrent logins and token refresh race conditions",
        "learnings": "Learned about JWT security best practices and token rotation strategies",
        "commit_metadata": {
            "hash": "abc123def456",
            "author": "Test Author <test@example.com>",
            "timestamp": "2024-01-15T10:30:00Z",
            "message": "feat: add user authentication",
        },
    }


@pytest.fixture
def partial_reflection() -> Dict:
    """
    Partial reflection with only some fields completed.

    Useful for testing session recovery and validation.
    """
    return {
        "commit_hash": "def456abc789",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "what_changed": "Fixed authentication bug",
        "why_changed": "Users reported issues with special characters",
        # Missing: how_changed, challenges, learnings
    }


# ============================================================================
# Storage Fixtures
# ============================================================================


@pytest.fixture
def temp_jsonl_file(tmp_path: Path) -> Path:
    """
    Temporary JSONL file for testing storage operations.

    Args:
        tmp_path: pytest's tmp_path fixture

    Returns:
        Path to temporary JSONL file
    """
    jsonl_file = tmp_path / "reflections.jsonl"
    jsonl_file.touch()
    return jsonl_file


@pytest.fixture
def temp_sqlite_db(tmp_path: Path) -> Path:
    """
    Temporary SQLite database file for testing.

    Args:
        tmp_path: pytest's tmp_path fixture

    Returns:
        Path to temporary SQLite database
    """
    db_file = tmp_path / "reflections.db"
    return db_file


@pytest.fixture
def jsonl_with_sample_data(temp_jsonl_file: Path, sample_reflection: Dict) -> Path:
    """
    JSONL file pre-populated with sample reflection data.

    Args:
        temp_jsonl_file: Temporary JSONL file fixture
        sample_reflection: Sample reflection fixture

    Returns:
        Path to JSONL file with sample data
    """
    with open(temp_jsonl_file, "w") as f:
        json.dump(sample_reflection, f)
        f.write("\n")
    return temp_jsonl_file


# ============================================================================
# Configuration Fixtures
# ============================================================================


@pytest.fixture
def minimal_config() -> Dict:
    """
    Minimal valid configuration for testing.

    Represents the absolute minimum configuration needed
    to run the commit reflection system.
    """
    return {
        "version": "1.0",
        "storage": {
            "backends": [{"type": "jsonl", "path": "reflections.jsonl"}]
        },
        "questions": [
            {"id": "what", "text": "What changed?", "type": "text"},
            {"id": "why", "text": "Why did it change?", "type": "text"},
        ],
    }


@pytest.fixture
def full_config(tmp_path: Path) -> Dict:
    """
    Full configuration with all optional fields.

    Useful for testing complete configuration parsing
    and validation.
    """
    return {
        "version": "1.0",
        "storage": {
            "backends": [
                {"type": "jsonl", "path": str(tmp_path / "reflections.jsonl")},
                {"type": "sqlite", "path": str(tmp_path / "reflections.db")},
            ],
            "primary": "jsonl",
        },
        "questions": [
            {"id": "what", "text": "What changed?", "type": "text", "required": True},
            {"id": "why", "text": "Why did it change?", "type": "text", "required": True},
            {
                "id": "how",
                "text": "How was it implemented?",
                "type": "text",
                "required": False,
            },
            {
                "id": "challenges",
                "text": "What challenges did you face?",
                "type": "text",
                "required": False,
            },
            {
                "id": "learnings",
                "text": "What did you learn?",
                "type": "text",
                "required": False,
            },
        ],
        "git": {"auto_detect_commit": True, "include_diff": False},
        "session": {"timeout_seconds": 300, "allow_partial_save": True},
    }


# ============================================================================
# Mock Storage Backend Fixtures
# ============================================================================


@pytest.fixture
def mock_storage_backend():
    """
    Mock storage backend for testing without actual I/O.

    Provides a mock object with all required storage backend methods.
    """
    mock = Mock()
    mock.write = Mock(return_value=True)
    mock.read = Mock(return_value=[])
    mock.read_recent = Mock(return_value=[])
    mock.health_check = Mock(return_value=True)
    return mock


# ============================================================================
# Test Data Generators
# ============================================================================


@pytest.fixture
def generate_reflections():
    """
    Factory fixture for generating multiple test reflections.

    Returns a function that generates N reflection objects with
    unique commit hashes and varying content.
    """

    def _generate(count: int = 5) -> List[Dict]:
        reflections = []
        for i in range(count):
            reflection = {
                "commit_hash": f"hash{i:03d}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "what_changed": f"Change number {i}",
                "why_changed": f"Reason number {i}",
                "how_changed": f"Implementation {i}",
            }
            reflections.append(reflection)
        return reflections

    return _generate


@pytest.fixture
def generate_commit_metadata():
    """
    Factory fixture for generating mock commit metadata.

    Returns a function that generates N commit metadata objects
    with realistic data.
    """

    def _generate(count: int = 5) -> List[Dict]:
        commits = []
        for i in range(count):
            commit = {
                "hash": f"commit{i:03d}",
                "author": f"Author {i} <author{i}@example.com>",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "message": f"Commit message {i}",
                "files_changed": [f"file{j}.py" for j in range(i + 1)],
                "insertions": (i + 1) * 10,
                "deletions": (i + 1) * 5,
                "branch": f"feature/branch-{i}",
            }
            commits.append(commit)
        return commits

    return _generate


@pytest.fixture
def sample_reflection_object():
    """
    Sample Reflection object for testing.

    Returns a complete Reflection object with all required fields.
    """
    from uuid import uuid4
    from shared.types.reflection import (
        Reflection,
        ReflectionAnswer,
        CommitContext,
        SessionMetadata,
    )

    now = datetime.now(timezone.utc)
    return Reflection(
        id=uuid4(),
        answers=[
            ReflectionAnswer(
                question_id="ai_synergy",
                question_text="How well did you and AI work together?",
                answer="4",
                answered_at=now,
            ),
            ReflectionAnswer(
                question_id="confidence",
                question_text="How confident are you in these changes?",
                answer="5",
                answered_at=now,
            ),
            ReflectionAnswer(
                question_id="experience",
                question_text="How did this work feel?",
                answer="Smooth and efficient",
                answered_at=now,
            ),
        ],
        commit_context=CommitContext(
            commit_hash="abc123def456",
            commit_message="feat: add user authentication",
            branch="feature/auth",
            author_name="Test Author",
            author_email="test@example.com",
            timestamp=now,
            files_changed=3,
            insertions=150,
            deletions=20,
            changed_files=["src/auth.py", "tests/test_auth.py"],
        ),
        session_metadata=SessionMetadata(
            session_id=uuid4(),
            started_at=now,
            completed_at=now,
            project_name="my-project",
            tool_version="0.1.0",
            environment="cli",
        ),
        created_at=now,
        updated_at=now,
    )
