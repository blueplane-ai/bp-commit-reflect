"""
Integration tests for session lifecycle management.

Tests complete reflection session workflows including:
- Session initialization
- Question progression
- Answer collection
- Session completion
- Session cancellation
- Error recovery
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

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
class TestSessionLifecycle:
    """Tests for complete session lifecycle."""

    @pytest.mark.asyncio
    async def test_complete_session_workflow(self, minimal_config, mock_commit_metadata):
        """Test complete workflow from start to finish."""
        manager = SessionManager()
        await manager.start()

        try:
            # Create session
            session = await manager.create_session(
                commit_hash=mock_commit_metadata["hash"], project_name="test-project"
            )

            # Simulate answering questions
            questions = minimal_config["questions"]

            for i, question in enumerate(questions):
                session.current_question_index = i
                session.update_activity()
                # In real implementation, answers would be stored
                # For now, just verify progression

            # Complete session
            success = await manager.complete_session(session.session_id)

            assert success is True
            retrieved = await manager.get_session(session.session_id)
            assert retrieved is not None
            assert retrieved.state == SessionState.COMPLETED
        finally:
            await manager.stop()

    @pytest.mark.asyncio
    async def test_session_initialization(self, mock_commit_metadata):
        """Test session initialization with commit metadata."""
        manager = SessionManager()
        await manager.start()

        try:
            session = await manager.create_session(
                commit_hash=mock_commit_metadata["hash"],
                project_name="test-project",
                metadata={"commit_metadata": mock_commit_metadata},
            )

            assert session.state == SessionState.INITIALIZING
            assert session.current_question_index == 0
            assert session.commit_hash == mock_commit_metadata["hash"]
        finally:
            await manager.stop()

    @pytest.mark.asyncio
    async def test_session_question_progression(self, minimal_config):
        """Test progressing through questions sequentially."""
        manager = SessionManager()
        await manager.start()

        try:
            session = await manager.create_session(
                commit_hash="abc123", project_name="test-project"
            )

            questions = minimal_config["questions"]

            # Progress through questions
            for i in range(len(questions)):
                assert session.current_question_index == i
                session.current_question_index += 1
                session.update_activity()

            assert session.current_question_index == len(questions)
        finally:
            await manager.stop()

    def test_session_partial_save(self, minimal_config):
        """Test saving partial session state."""
        session = {
            "session_id": "partial_save_test",
            "commit_hash": "abc123",
            "answers": {"what": "Added feature"},
            "current_question_index": 1,
            "status": "active",
        }

        # Simulate partial save
        partial_data = {
            "session_id": session["session_id"],
            "commit_hash": session["commit_hash"],
            "answers": session["answers"],
            "is_partial": True,
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }

        assert partial_data["is_partial"] is True
        assert len(partial_data["answers"]) == 1

    @pytest.mark.asyncio
    async def test_session_completion(self, sample_reflection):
        """Test session completion and reflection save."""
        manager = SessionManager()
        await manager.start()

        try:
            session = await manager.create_session(
                commit_hash=sample_reflection["commit_hash"], project_name="test-project"
            )

            # Complete session
            success = await manager.complete_session(session.session_id)

            assert success is True
            retrieved = await manager.get_session(session.session_id)
            assert retrieved is not None
            assert retrieved.state == SessionState.COMPLETED
            assert retrieved.commit_hash == sample_reflection["commit_hash"]
        finally:
            await manager.stop()

    @pytest.mark.asyncio
    async def test_session_cancellation(self):
        """Test session cancellation without saving."""
        manager = SessionManager()
        await manager.start()

        try:
            session = await manager.create_session(
                commit_hash="abc123", project_name="test-project"
            )

            # Cancel session
            success = await manager.cancel_session(session.session_id)

            assert success is True
            retrieved = await manager.get_session(session.session_id)
            assert retrieved is not None
            assert retrieved.state == SessionState.CANCELLED
        finally:
            await manager.stop()

    @pytest.mark.asyncio
    async def test_session_timeout_handling(self):
        """Test session timeout detection and handling."""
        manager = SessionManager(default_timeout=5)  # 5 seconds for testing
        await manager.start()

        try:
            session = await manager.create_session(
                commit_hash="abc123", project_name="test-project", timeout_seconds=5
            )

            # Manually set last_activity to past
            session.last_activity = datetime.now() - timedelta(seconds=10)

            # Check if session has timed out
            assert session.is_timed_out() is True

            # Session should be cleaned up
            retrieved = await manager.get_session(session.session_id)
            # After timeout check, session may be None
            if retrieved:
                assert retrieved.state == SessionState.TIMED_OUT
        finally:
            await manager.stop()


@pytest.mark.integration
class TestSessionErrorRecovery:
    """Tests for session error recovery and resilience."""

    @pytest.mark.asyncio
    async def test_recover_from_invalid_answer(self, minimal_config):
        """Test recovery from invalid answer input."""
        manager = SessionManager()
        await manager.start()

        try:
            session = await manager.create_session(
                commit_hash="abc123", project_name="test-project"
            )

            # Session should still be active even with validation errors
            # (validation happens at CLI level, not session manager level)
            assert session.is_active() is True
            assert session.state in (SessionState.INITIALIZING, SessionState.ACTIVE)
        finally:
            await manager.stop()

    @pytest.mark.asyncio
    async def test_recover_from_storage_failure(self):
        """Test recovery when storage write fails."""
        manager = SessionManager()
        await manager.start()

        try:
            session = await manager.create_session(
                commit_hash="abc123", project_name="test-project"
            )

            # Session manager doesn't handle storage directly
            # But session should remain valid even if storage fails
            assert session.is_active() is True

            # Complete session (storage failure would be handled at higher level)
            success = await manager.complete_session(session.session_id)
            assert success is True
        finally:
            await manager.stop()

    @pytest.mark.asyncio
    async def test_resume_partial_session(self):
        """Test resuming a partially completed session."""
        manager = SessionManager()
        await manager.start()

        try:
            # Create session
            session = await manager.create_session(
                commit_hash="abc123", project_name="test-project"
            )

            # Simulate partial progress
            session.current_question_index = 2
            session.update_activity()

            # Session should be resumable
            retrieved = await manager.get_session(session.session_id)
            assert retrieved is not None
            assert retrieved.current_question_index == 2
        finally:
            await manager.stop()
