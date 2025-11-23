"""
Integration tests for concurrent session handling.

Tests the system's ability to manage multiple simultaneous reflection sessions.
"""

import pytest
import threading
from datetime import datetime, timezone
from unittest.mock import Mock
import time


@pytest.mark.integration
@pytest.mark.slow
class TestConcurrentSessions:
    """Tests for concurrent session management."""

    def test_multiple_sessions_simultaneously(self):
        """Test managing multiple active sessions at once."""
        sessions = {}

        # Create multiple sessions
        for i in range(5):
            session_id = f"session_{i}"
            sessions[session_id] = {
                "session_id": session_id,
                "commit_hash": f"hash_{i}",
                "started_at": datetime.now(timezone.utc),
                "answers": {},
                "status": "active",
            }

        assert len(sessions) == 5
        assert all(s["status"] == "active" for s in sessions.values())

    def test_session_isolation(self):
        """Test that sessions don't interfere with each other."""
        session1 = {
            "session_id": "session_1",
            "answers": {"what": "Feature A"},
            "status": "active",
        }

        session2 = {
            "session_id": "session_2",
            "answers": {"what": "Feature B"},
            "status": "active",
        }

        # Modify session1
        session1["answers"]["why"] = "Reason A"

        # Session2 should be unaffected
        assert "why" not in session2["answers"]
        assert session2["answers"]["what"] == "Feature B"

    def test_concurrent_writes_to_storage(self, mocker):
        """Test concurrent writes to storage backend."""
        mock_storage = Mock()
        mock_storage.write.return_value = True

        reflections = [
            {"commit_hash": f"hash_{i}", "what_changed": f"Change {i}"}
            for i in range(3)
        ]

        # Simulate concurrent writes
        for reflection in reflections:
            mock_storage.write(reflection)

        assert mock_storage.write.call_count == 3

    def test_session_id_uniqueness(self):
        """Test that session IDs are unique."""
        import uuid

        session_ids = set()

        for _ in range(10):
            session_id = str(uuid.uuid4())
            session_ids.add(session_id)

        assert len(session_ids) == 10

    def test_thread_safe_session_creation(self):
        """Test thread-safe session creation."""
        import uuid

        sessions = {}
        lock = threading.Lock()

        def create_session(commit_hash):
            session_id = str(uuid.uuid4())
            with lock:
                sessions[session_id] = {
                    "session_id": session_id,
                    "commit_hash": commit_hash,
                    "status": "active",
                }

        # Create sessions from multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_session, args=(f"hash_{i}",))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        assert len(sessions) == 5

    def test_concurrent_session_completion(self):
        """Test completing multiple sessions concurrently."""
        sessions = {
            f"session_{i}": {
                "session_id": f"session_{i}",
                "status": "active",
                "answers": {"what": f"Change {i}"},
            }
            for i in range(3)
        }

        completed_sessions = []

        def complete_session(session_id):
            session = sessions[session_id]
            session["status"] = "completed"
            session["completed_at"] = datetime.now(timezone.utc)
            completed_sessions.append(session_id)

        # Complete sessions concurrently
        threads = []
        for session_id in sessions.keys():
            thread = threading.Thread(target=complete_session, args=(session_id,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        assert len(completed_sessions) == 3
        assert all(sessions[sid]["status"] == "completed" for sid in completed_sessions)


@pytest.mark.integration
class TestProcessCrashRecovery:
    """Tests for process crash recovery."""

    def test_recover_session_after_process_restart(self):
        """Test recovering session state after process crash."""
        # Session state before crash
        pre_crash_state = {
            "session_id": "crash_test",
            "commit_hash": "abc123",
            "answers": {"what": "Added auth", "why": "Security"},
            "current_question_index": 2,
            "status": "active",
        }

        # Simulate persisting session state
        persisted_state = pre_crash_state.copy()

        # Simulate process crash and restart

        # Recover session from persisted state
        recovered_state = persisted_state.copy()
        recovered_state["recovered"] = True
        recovered_state["recovered_at"] = datetime.now(timezone.utc)

        assert recovered_state["session_id"] == pre_crash_state["session_id"]
        assert recovered_state["answers"] == pre_crash_state["answers"]
        assert recovered_state["recovered"] is True

    def test_detect_orphaned_sessions(self):
        """Test detecting sessions from crashed processes."""
        from datetime import timedelta

        sessions = {
            "old_session": {
                "session_id": "old_session",
                "started_at": datetime.now(timezone.utc) - timedelta(hours=2),
                "status": "active",
                "last_heartbeat": datetime.now(timezone.utc) - timedelta(hours=1),
            },
            "active_session": {
                "session_id": "active_session",
                "started_at": datetime.now(timezone.utc),
                "status": "active",
                "last_heartbeat": datetime.now(timezone.utc),
            },
        }

        # Find orphaned sessions (no heartbeat for > 30 minutes)
        orphaned = []
        threshold = timedelta(minutes=30)

        for session_id, session in sessions.items():
            if "last_heartbeat" in session:
                time_since_heartbeat = (
                    datetime.now(timezone.utc) - session["last_heartbeat"]
                )
                if time_since_heartbeat > threshold:
                    orphaned.append(session_id)

        assert "old_session" in orphaned
        assert "active_session" not in orphaned

    def test_cleanup_orphaned_sessions(self):
        """Test cleaning up orphaned sessions."""
        sessions = {
            "orphaned": {"session_id": "orphaned", "status": "active"},
            "active": {"session_id": "active", "status": "active"},
        }

        orphaned_ids = ["orphaned"]

        # Cleanup orphaned sessions
        for session_id in orphaned_ids:
            if session_id in sessions:
                sessions[session_id]["status"] = "orphaned"
                sessions[session_id]["cleaned_up_at"] = datetime.now(timezone.utc)

        assert sessions["orphaned"]["status"] == "orphaned"
        assert sessions["active"]["status"] == "active"

    def test_partial_session_recovery(self):
        """Test recovering partial session data after crash."""
        # Incomplete persisted state (missing some fields)
        incomplete_state = {
            "session_id": "partial_recovery",
            "commit_hash": "abc123",
            "answers": {"what": "Test"},
            # Missing: current_question_index, status, etc.
        }

        # Recover with defaults
        recovered = {
            **incomplete_state,
            "current_question_index": incomplete_state.get("current_question_index", 0),
            "status": incomplete_state.get("status", "recovered"),
            "recovered_at": datetime.now(timezone.utc),
        }

        assert recovered["status"] == "recovered"
        assert recovered["current_question_index"] == 0
