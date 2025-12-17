"""Integration tests for end-to-end workflows."""

import sys
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from packages.cli.src.progress import ProgressIndicator
from packages.cli.src.validators import validate_question_answer
from packages.shared.storage.jsonl import JSONLStorage


class TestEndToEndWorkflow:
    """Test complete reflection workflow from start to finish."""

    def test_complete_reflection_flow(self, temp_dir, sample_reflection):
        """Test full reflection capture workflow."""
        # 1. Initialize storage
        jsonl_path = temp_dir / "reflections.jsonl"
        storage = JSONLStorage(str(jsonl_path))

        # 2. Write reflection
        success = storage.write(sample_reflection)
        assert success is True

        # 3. Verify data integrity
        assert jsonl_path.exists()

        # 4. Read back and verify
        reflections = storage.read_recent(limit=1)
        assert len(reflections) == 1
        assert reflections[0]["commit_hash"] == sample_reflection["commit_hash"]
        assert reflections[0]["project"] == sample_reflection["project"]

        storage.close()

    def test_recovery_workflow(self):
        """Test session recovery after interruption."""
        pass  # Placeholder

    def test_multi_backend_storage(self):
        """Test writing to multiple storage backends."""
        pass  # Placeholder


class TestJSONLIntegration:
    """Integration tests for JSONL storage."""

    def test_jsonl_atomic_write(self, temp_dir):
        """Test atomic write operations to JSONL."""
        jsonl_path = temp_dir / "test.jsonl"
        storage = JSONLStorage(str(jsonl_path))

        reflection = {
            "project": "test-project",
            "commit_hash": "abc123",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "reflections": {"ai_synergy": 4, "confidence": 5},
        }

        success = storage.write(reflection)
        assert success is True
        assert jsonl_path.exists()

        # Verify content
        reflections = storage.read_recent(limit=1)
        assert len(reflections) == 1
        assert reflections[0]["commit_hash"] == "abc123"

        storage.close()

    def test_jsonl_concurrent_access(self):
        """Test file locking for concurrent access."""
        pass  # Placeholder

    def test_jsonl_read_operations(self):
        """Test reading historical reflections."""
        pass  # Placeholder


class TestValidationIntegration:
    """Integration tests for validation system."""

    def test_scale_validation_workflow(self, sample_questions):
        """Test scale question validation in workflow."""
        scale_question = sample_questions[0]  # ai_synergy

        # Valid answer
        validated, error = validate_question_answer(scale_question, "4")
        assert error is None
        assert validated == 4

        # Invalid answer - out of range
        validated, error = validate_question_answer(scale_question, "10")
        assert error is not None
        assert validated is None

        # Invalid answer - not a number
        validated, error = validate_question_answer(scale_question, "not a number")
        assert error is not None
        assert validated is None

    def test_text_validation_workflow(self, sample_questions):
        """Test text question validation in workflow."""
        text_question = sample_questions[2]  # experience

        # Valid answer
        validated, error = validate_question_answer(text_question, "Great experience")
        assert error is None
        assert validated == "Great experience"

        # Empty answer (not allowed for required)
        validated, error = validate_question_answer(text_question, "")
        assert error is not None
        assert validated is None

        # Too long answer
        long_text = "x" * 600
        validated, error = validate_question_answer(text_question, long_text)
        assert error is not None
        assert validated is None

    def test_error_recovery_workflow(self, temp_dir):
        """Test error recovery mechanisms."""
        # Test that storage failures don't crash the system
        jsonl_path = temp_dir / "reflections.jsonl"
        storage = JSONLStorage(str(jsonl_path))

        # Write valid reflection
        reflection = {
            "project": "test",
            "commit_hash": "abc123",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        success = storage.write(reflection)
        assert success is True

        # System should handle read errors gracefully
        reflections = storage.read_recent(limit=10)
        assert isinstance(reflections, list)

        storage.close()


class TestCrossPlatform:
    """Cross-platform compatibility tests."""

    def test_path_handling_windows(self):
        """Test path handling on Windows-style paths."""
        pass  # Placeholder

    def test_path_handling_unix(self):
        """Test path handling on Unix-style paths."""
        pass  # Placeholder

    def test_color_output_detection(self):
        """Test terminal color detection across platforms."""
        pass  # Placeholder


class TestUserExperience:
    """User experience validation tests."""

    def test_progress_indicator_display(self):
        """Test progress indicator displays correctly."""
        progress = ProgressIndicator(total_questions=5, use_color=False)

        # Test welcome message
        progress.show_welcome("test-project", "abc123def456")

        # Test question display
        progress.show_question(1, "Question 1", help_text="Help text", optional=False)
        progress.show_question(2, "Question 2", optional=True)

        # Test progress tracking
        assert progress.current_question == 2

    def test_error_message_clarity(self):
        """Test error messages are clear and helpful."""
        progress = ProgressIndicator(use_color=False)

        # Test error display with help text
        progress.show_error("Validation failed", "Please enter a number between 1 and 5")

        # Test error display without help text
        progress.show_error("Storage error")

    def test_help_text_display(self):
        """Test help text is displayed appropriately."""
        progress = ProgressIndicator(use_color=False)

        # Test question with help text
        progress.show_question(
            1, "How confident are you?", help_text="Rate from 1 to 5", optional=False
        )

        # Test question without help text
        progress.show_question(2, "What did you learn?", optional=True)


class TestPerformance:
    """Performance profiling tests."""

    def test_jsonl_write_performance(self, temp_dir):
        """Test JSONL write performance with large files."""
        import time

        jsonl_path = temp_dir / "perf.jsonl"
        storage = JSONLStorage(str(jsonl_path))

        # Write multiple reflections and measure time
        start = time.perf_counter()
        for i in range(100):
            reflection = {
                "project": "test",
                "commit_hash": f"abc{i:03d}",
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
            storage.write(reflection)

        elapsed = time.perf_counter() - start
        avg_time_ms = (elapsed / 100) * 1000

        # Should be fast (< 100ms per write)
        assert avg_time_ms < 100, f"Write too slow: {avg_time_ms:.2f}ms"

        storage.close()

    def test_session_memory_usage(self):
        """Test session memory footprint."""
        # Basic memory test - just verify objects can be created
        progress = ProgressIndicator(total_questions=5)
        assert progress.total_questions == 5

        # Memory usage is minimal for session objects
        # More detailed memory profiling would require memory_profiler

    def test_startup_time(self):
        """Test CLI startup time."""
        import time

        # Test that basic imports and initialization are fast
        start = time.perf_counter()
        from packages.cli.src.progress import ProgressIndicator

        ProgressIndicator()
        elapsed = time.perf_counter() - start

        # Should be very fast (< 100ms)
        assert elapsed < 0.1, f"Startup too slow: {elapsed*1000:.2f}ms"


class TestMCPIntegration:
    """Integration tests for MCP mode."""

    def test_mcp_session_lifecycle(self):
        """Test complete MCP session lifecycle."""
        pass  # Placeholder

    def test_mcp_message_protocol(self):
        """Test MCP JSON message protocol."""
        pass  # Placeholder

    def test_mcp_error_handling(self):
        """Test MCP error response format."""
        pass  # Placeholder

    def test_mcp_state_serialization(self):
        """Test session state serialization for MCP."""
        pass  # Placeholder


# Test fixtures


@pytest.fixture
def temp_storage_dir():
    """Provide temporary directory for storage tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_reflection():
    """Provide sample reflection data."""
    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "project": "test-project",
        "branch": "main",
        "commit_hash": "abc123def456",
        "commit_message": "Add new feature",
        "reflections": {
            "ai_synergy": 4,
            "confidence": 5,
            "experience": "Smooth development process",
            "blockers": None,
            "learning": "Learned about async patterns",
        },
    }


@pytest.fixture
def sample_questions():
    """Provide sample question configuration."""
    return [
        {
            "id": "ai_synergy",
            "prompt": "How well did you and AI work together?",
            "type": "scale",
            "range": [1, 5],
            "optional": False,
        },
        {
            "id": "confidence",
            "prompt": "How confident are you in these changes?",
            "type": "scale",
            "range": [1, 5],
            "optional": False,
        },
        {
            "id": "experience",
            "prompt": "How did this work feel?",
            "type": "text",
            "max_length": 512,
            "optional": False,
        },
    ]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
