"""Performance profiling tests."""

import tempfile
import time
from pathlib import Path

import pytest


class TestStoragePerformance:
    """Test storage backend performance."""

    def test_jsonl_write_speed(self, temp_dir):
        """Measure JSONL write performance."""
        # Target: < 100ms for single write
        import time
        from datetime import datetime

        from packages.shared.storage.jsonl import JSONLStorage

        jsonl_path = temp_dir / "perf.jsonl"
        storage = JSONLStorage(str(jsonl_path))

        reflection = {
            "project": "test",
            "commit_hash": "abc123",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        start = time.perf_counter()
        success = storage.write(reflection)
        elapsed = (time.perf_counter() - start) * 1000  # Convert to ms

        assert success is True
        assert elapsed < 100, f"Write too slow: {elapsed:.2f}ms"

        storage.close()

    def test_jsonl_read_speed(self, temp_dir):
        """Measure JSONL read performance."""
        # Target: < 50ms to read 100 entries
        import time
        from datetime import datetime

        from packages.shared.storage.jsonl import JSONLStorage

        jsonl_path = temp_dir / "perf.jsonl"
        storage = JSONLStorage(str(jsonl_path))

        # Write 100 entries
        for i in range(100):
            reflection = {
                "project": "test",
                "commit_hash": f"abc{i:03d}",
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
            storage.write(reflection)

        # Measure read time
        start = time.perf_counter()
        reflections = storage.read_recent(limit=100)
        elapsed = (time.perf_counter() - start) * 1000  # Convert to ms

        assert len(reflections) == 100
        assert elapsed < 50, f"Read too slow: {elapsed:.2f}ms"

        storage.close()


class TestSessionPerformance:
    """Test session handling performance."""

    def test_session_startup_time(self):
        """Measure session initialization time."""
        # Target: < 500ms startup
        pass

    def test_session_memory_usage(self):
        """Measure session memory footprint."""
        # Target: < 50MB memory usage
        pass

    def test_concurrent_session_handling(self):
        """Test handling multiple concurrent sessions."""
        pass


class TestValidationPerformance:
    """Test validation system performance."""

    def test_validation_speed(self):
        """Measure validation operation speed."""
        # Target: < 1ms per validation
        import time

        from packages.cli.src.validators import validate_scale, validate_text

        # Test scale validation speed
        start = time.perf_counter()
        for _ in range(1000):
            validate_scale(3, 1, 5)
        elapsed = (time.perf_counter() - start) / 1000 * 1000  # ms per validation

        assert elapsed < 1, f"Validation too slow: {elapsed:.3f}ms"

        # Test text validation speed
        start = time.perf_counter()
        for _ in range(1000):
            validate_text("test answer", max_length=512)
        elapsed = (time.perf_counter() - start) / 1000 * 1000

        assert elapsed < 1, f"Text validation too slow: {elapsed:.3f}ms"

    def test_bulk_validation_performance(self):
        """Test validation of multiple inputs."""
        import time

        from packages.cli.src.validators import validate_question_answer

        question = {"id": "test", "type": "scale", "range": [1, 5], "optional": False}

        answers = ["1", "2", "3", "4", "5"] * 100  # 500 answers

        start = time.perf_counter()
        for answer in answers:
            validate_question_answer(question, answer)
        elapsed = time.perf_counter() - start

        # Should handle 500 validations quickly
        assert elapsed < 1, f"Bulk validation too slow: {elapsed:.2f}s"


class TestMCPPerformance:
    """Test MCP mode performance."""

    def test_message_processing_speed(self):
        """Measure MCP message processing speed."""
        # Target: < 10ms per message
        pass

    def test_state_serialization_speed(self):
        """Measure state serialization performance."""
        pass


# Performance benchmarking utilities


@pytest.fixture
def benchmark_storage():
    """Provide storage for benchmarking."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def measure_time(func, iterations=100):
    """
    Measure average execution time of a function.

    Args:
        func: Function to measure
        iterations: Number of iterations

    Returns:
        Average time in milliseconds
    """
    start = time.perf_counter()
    for _ in range(iterations):
        func()
    end = time.perf_counter()

    avg_time_ms = ((end - start) / iterations) * 1000
    return avg_time_ms


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
