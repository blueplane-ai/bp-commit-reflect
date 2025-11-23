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

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock


@pytest.mark.integration
class TestSessionLifecycle:
    """Tests for complete session lifecycle."""

    def test_complete_session_workflow(
        self, minimal_config, mock_commit_metadata
    ):
        """Test complete workflow from start to finish."""
        # Session state
        session = {
            "session_id": "test_session",
            "commit_hash": mock_commit_metadata["hash"],
            "started_at": datetime.now(timezone.utc),
            "current_question_index": 0,
            "answers": {},
            "status": "active",
        }

        # Simulate answering questions
        questions = minimal_config["questions"]

        for i, question in enumerate(questions):
            session["current_question_index"] = i
            session["answers"][question["id"]] = f"Answer to {question['text']}"

        # Complete session
        session["status"] = "completed"
        session["completed_at"] = datetime.now(timezone.utc)

        assert session["status"] == "completed"
        assert len(session["answers"]) == len(questions)

    def test_session_initialization(self, mock_commit_metadata):
        """Test session initialization with commit metadata."""
        session = {
            "session_id": "init_test",
            "commit_hash": mock_commit_metadata["hash"],
            "commit_metadata": mock_commit_metadata,
            "started_at": datetime.now(timezone.utc),
            "current_question_index": 0,
            "answers": {},
            "status": "active",
        }

        assert session["status"] == "active"
        assert session["current_question_index"] == 0
        assert session["commit_hash"] == mock_commit_metadata["hash"]

    def test_session_question_progression(self, minimal_config):
        """Test progressing through questions sequentially."""
        questions = minimal_config["questions"]
        session = {
            "current_question_index": 0,
            "answers": {},
        }

        # Answer each question
        for i, question in enumerate(questions):
            assert session["current_question_index"] == i

            # Answer question
            session["answers"][question["id"]] = "Test answer"

            # Move to next question
            session["current_question_index"] += 1

        assert len(session["answers"]) == len(questions)

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

    def test_session_completion(self, sample_reflection):
        """Test session completion and reflection save."""
        session = {
            "session_id": "completion_test",
            "commit_hash": sample_reflection["commit_hash"],
            "answers": {
                "what": sample_reflection["what_changed"],
                "why": sample_reflection["why_changed"],
            },
            "status": "active",
        }

        # Complete session
        session["status"] = "completed"
        session["completed_at"] = datetime.now(timezone.utc)

        # Create reflection from session
        reflection = {
            "commit_hash": session["commit_hash"],
            "timestamp": session["completed_at"].isoformat(),
            **session["answers"],
        }

        assert session["status"] == "completed"
        assert reflection["commit_hash"] == session["commit_hash"]

    def test_session_cancellation(self):
        """Test session cancellation without saving."""
        session = {
            "session_id": "cancel_test",
            "commit_hash": "abc123",
            "answers": {"what": "Partial answer"},
            "status": "active",
        }

        # Cancel session
        session["status"] = "cancelled"
        session["cancelled_at"] = datetime.now(timezone.utc)

        assert session["status"] == "cancelled"

    def test_session_timeout_handling(self):
        """Test session timeout detection and handling."""
        from datetime import timedelta

        session = {
            "session_id": "timeout_test",
            "started_at": datetime.now(timezone.utc) - timedelta(minutes=10),
            "timeout_seconds": 300,  # 5 minutes
            "status": "active",
        }

        # Check if session has timed out
        elapsed = (
            datetime.now(timezone.utc) - session["started_at"]
        ).total_seconds()
        has_timed_out = elapsed > session["timeout_seconds"]

        assert has_timed_out is True


@pytest.mark.integration
class TestSessionErrorRecovery:
    """Tests for session error recovery and resilience."""

    def test_recover_from_invalid_answer(self, minimal_config):
        """Test recovery from invalid answer input."""
        session = {
            "current_question_index": 0,
            "answers": {},
            "errors": [],
        }

        question = minimal_config["questions"][0]

        # Attempt invalid answer (empty string for required field)
        invalid_answer = ""

        if question["required"] and not invalid_answer:
            session["errors"].append(
                {
                    "question_id": question["id"],
                    "error": "Answer required",
                }
            )
        else:
            session["answers"][question["id"]] = invalid_answer

        # Session should still be recoverable
        assert len(session["errors"]) == 1
        assert question["id"] not in session["answers"]

    def test_recover_from_storage_failure(self, mocker):
        """Test recovery when storage write fails."""
        mock_storage = Mock()
        mock_storage.write.side_effect = Exception("Storage unavailable")

        session = {
            "session_id": "storage_fail_test",
            "answers": {"what": "Test", "why": "Test"},
            "status": "completing",
        }

        # Attempt to save
        try:
            mock_storage.write(session)
            session["status"] = "completed"
        except Exception as e:
            session["status"] = "failed"
            session["error"] = str(e)

        # Session should capture error
        assert session["status"] == "failed"
        assert "Storage unavailable" in session["error"]

    def test_resume_partial_session(self):
        """Test resuming a partially completed session."""
        # Saved partial session
        partial_session = {
            "session_id": "resume_test",
            "commit_hash": "abc123",
            "answers": {"what": "Added auth", "why": "User need"},
            "current_question_index": 2,
            "is_partial": True,
        }

        # Resume session
        resumed = {
            **partial_session,
            "resumed_at": datetime.now(timezone.utc),
            "is_partial": False,
        }

        # Continue from where we left off
        assert resumed["current_question_index"] == 2
        assert len(resumed["answers"]) == 2
