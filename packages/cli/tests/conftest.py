"""Pytest configuration and shared fixtures."""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime


@pytest.fixture
def temp_dir():
    """Provide a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_commit_data():
    """Provide mock commit data."""
    return {
        "hash": "abc123def456789",
        "message": "Add user authentication feature",
        "author": "Test User",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "files_changed": [
            "src/auth/login.py",
            "tests/test_auth.py"
        ],
        "lines_added": 127,
        "lines_removed": 12
    }


@pytest.fixture
def mock_reflection_data():
    """Provide mock reflection data."""
    return {
        "ai_synergy": 4,
        "confidence": 5,
        "experience": "Development went smoothly with good AI assistance",
        "blockers": "Minor documentation issues",
        "learning": "Learned about JWT token handling"
    }


@pytest.fixture
def mock_session_state():
    """Provide mock session state."""
    return {
        "session_id": "test-session-123",
        "project": "test-project",
        "branch": "feature/auth",
        "commit_hash": "abc123def456789",
        "current_question_index": 0,
        "answers": {},
        "started_at": datetime.utcnow().isoformat() + "Z",
        "status": "active"
    }


@pytest.fixture
def mock_config():
    """Provide mock configuration."""
    return {
        "storage": ["jsonl"],
        "jsonl_path": ".commit-reflections.jsonl",
        "db_path": "~/.commit-reflect/reflections.db",
        "questions": [
            {
                "id": "ai_synergy",
                "prompt": "How well did you and AI work together?",
                "type": "scale",
                "range": [1, 5],
                "optional": False,
                "help_text": "1 = AI hindered progress, 5 = Perfect collaboration"
            },
            {
                "id": "confidence",
                "prompt": "How confident are you in these changes?",
                "type": "scale",
                "range": [1, 5],
                "optional": False,
                "help_text": "1 = Not confident, 5 = Very confident"
            },
            {
                "id": "experience",
                "prompt": "How did this work feel?",
                "type": "text",
                "max_length": 512,
                "optional": False
            },
            {
                "id": "blockers",
                "prompt": "What blockers did you encounter?",
                "type": "text",
                "optional": True
            },
            {
                "id": "learning",
                "prompt": "What did you learn?",
                "type": "text",
                "optional": True
            }
        ]
    }


# Test markers

def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as performance test"
    )
    config.addinivalue_line(
        "markers", "ux: mark test as user experience test"
    )
    config.addinivalue_line(
        "markers", "cross_platform: mark test as cross-platform test"
    )
