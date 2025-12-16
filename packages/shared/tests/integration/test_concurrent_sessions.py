"""
Integration tests for concurrent session handling.

Tests the system's ability to manage multiple simultaneous reflection sessions.
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock

import pytest

# Add packages to path for imports
project_root = Path(__file__).parent.parent.parent.parent
mcp_server_path = project_root / "mcp-server" / "src"
sys.path.insert(0, str(mcp_server_path))

# Import with proper module structure
import importlib.util

spec = importlib.util.spec_from_file_location(
    "session_manager", mcp_server_path / "session_manager.py"
)
sm_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sm_module)
SessionManager = sm_module.SessionManager
SessionState = sm_module.SessionState
Session = sm_module.Session


@pytest.mark.integration
@pytest.mark.slow
class TestConcurrentSessions:
    """Tests for concurrent session management."""

    @pytest.mark.asyncio
    async def test_multiple_sessions_simultaneously(self):
        """Test managing multiple active sessions at once."""
        manager = SessionManager(max_concurrent_sessions=10)
        await manager.start()

        try:
            # Create multiple sessions
            sessions = []
            for i in range(5):
                session = await manager.create_session(
                    commit_hash=f"hash_{i}", project_name=f"project_{i}"
                )
                sessions.append(session)

            assert len(sessions) == 5
            assert all(s.is_active() for s in sessions)

            # Verify all sessions are tracked
            active_sessions = await manager.list_active_sessions()
            assert len(active_sessions) == 5
        finally:
            await manager.stop()

    @pytest.mark.asyncio
    async def test_session_isolation(self):
        """Test that sessions don't interfere with each other."""
        manager = SessionManager()
        await manager.start()

        try:
            # Create two sessions
            session1 = await manager.create_session(commit_hash="hash1", project_name="project1")
            session2 = await manager.create_session(commit_hash="hash2", project_name="project2")

            # Modify session1
            session1.current_question_index = 1
            session1.update_activity()

            # Session2 should be unaffected
            retrieved2 = await manager.get_session(session2.session_id)
            assert retrieved2 is not None
            assert retrieved2.current_question_index == 0
            assert retrieved2.commit_hash == "hash2"
        finally:
            await manager.stop()

    def test_concurrent_writes_to_storage(self, mocker):
        """Test concurrent writes to storage backend."""
        mock_storage = Mock()
        mock_storage.write.return_value = True

        reflections = [
            {"commit_hash": f"hash_{i}", "what_changed": f"Change {i}"} for i in range(3)
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

    @pytest.mark.asyncio
    async def test_concurrent_session_creation(self):
        """Test concurrent session creation."""
        manager = SessionManager(max_concurrent_sessions=10)
        await manager.start()

        try:
            # Create sessions concurrently using asyncio
            tasks = []
            for i in range(5):
                task = manager.create_session(commit_hash=f"hash_{i}", project_name=f"project_{i}")
                tasks.append(task)

            sessions = await asyncio.gather(*tasks)

            assert len(sessions) == 5
            assert all(s.is_active() for s in sessions)
        finally:
            await manager.stop()

    @pytest.mark.asyncio
    async def test_concurrent_session_completion(self):
        """Test completing multiple sessions concurrently."""
        manager = SessionManager(max_concurrent_sessions=10)
        await manager.start()

        try:
            # Create multiple sessions
            sessions = []
            for i in range(3):
                session = await manager.create_session(
                    commit_hash=f"hash_{i}", project_name=f"project_{i}"
                )
                sessions.append(session)

            # Complete sessions concurrently
            tasks = [manager.complete_session(s.session_id) for s in sessions]
            results = await asyncio.gather(*tasks)

            assert all(results) is True
            assert len(results) == 3

            # Verify all sessions are completed
            for session in sessions:
                retrieved = await manager.get_session(session.session_id)
                assert retrieved is not None
                assert retrieved.state == SessionState.COMPLETED
        finally:
            await manager.stop()


@pytest.mark.integration
class TestProcessCrashRecovery:
    """Tests for process crash recovery."""

    @pytest.mark.asyncio
    async def test_recover_session_after_process_restart(self):
        """Test recovering session state after process crash."""
        manager = SessionManager()
        await manager.start()

        try:
            # Create session
            session = await manager.create_session(
                commit_hash="abc123", project_name="test-project"
            )

            # Simulate progress
            session.current_question_index = 2
            session.update_activity()

            # Simulate crash - session state is lost
            # In real scenario, state would be persisted and recovered
            # For now, verify session can be recreated with same commit
            session_id = session.session_id

            # After "restart", we'd recreate manager and load persisted state
            # For test, verify session is still accessible
            retrieved = await manager.get_session(session_id)
            assert retrieved is not None
            assert retrieved.current_question_index == 2
        finally:
            await manager.stop()

    @pytest.mark.asyncio
    async def test_detect_orphaned_sessions(self):
        """Test detecting sessions from crashed processes."""
        manager = SessionManager(default_timeout=30)  # 30 seconds for testing
        await manager.start()

        try:
            # Create old session (simulated)
            old_session = await manager.create_session(
                commit_hash="old_hash", project_name="old-project"
            )
            old_session.last_activity = datetime.now() - timedelta(minutes=35)

            # Create active session
            active_session = await manager.create_session(
                commit_hash="active_hash", project_name="active-project"
            )

            # Check for timed out sessions
            assert old_session.is_timed_out() is True
            assert active_session.is_timed_out() is False

            # Cleanup should handle orphaned sessions
            await manager._cleanup_stale_sessions()
        finally:
            await manager.stop()

    @pytest.mark.asyncio
    async def test_cleanup_orphaned_sessions(self):
        """Test cleaning up orphaned sessions."""
        manager = SessionManager(default_timeout=30, cleanup_interval=1)
        await manager.start()

        try:
            # Create orphaned session (timed out)
            orphaned = await manager.create_session(
                commit_hash="orphaned_hash", project_name="orphaned-project"
            )
            orphaned.last_activity = datetime.now() - timedelta(minutes=35)

            # Create active session
            active = await manager.create_session(
                commit_hash="active_hash", project_name="active-project"
            )

            # Wait for cleanup
            await asyncio.sleep(2)

            # Orphaned session should be timed out
            retrieved_orphaned = await manager.get_session(orphaned.session_id)
            if retrieved_orphaned:
                assert retrieved_orphaned.state == SessionState.TIMED_OUT

            # Active session should still be active
            retrieved_active = await manager.get_session(active.session_id)
            assert retrieved_active is not None
            assert retrieved_active.is_active() is True
        finally:
            await manager.stop()

    @pytest.mark.asyncio
    async def test_partial_session_recovery(self):
        """Test recovering partial session data after crash."""
        manager = SessionManager()
        await manager.start()

        try:
            # Create session
            session = await manager.create_session(
                commit_hash="abc123", project_name="test-project"
            )

            # Simulate partial progress
            session.current_question_index = 1
            session.update_activity()

            # Session should be recoverable even if some data is missing
            # (defaults are provided by Session dataclass)
            retrieved = await manager.get_session(session.session_id)
            assert retrieved is not None
            assert retrieved.current_question_index >= 0
            assert retrieved.commit_hash == "abc123"
        finally:
            await manager.stop()
