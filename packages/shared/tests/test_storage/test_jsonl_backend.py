"""
Tests for JSONL storage backend.

Tests the JSONL storage implementation including atomic writes,
file locking, and read operations.
"""

import json
import pytest
from datetime import datetime, timezone
from pathlib import Path

from shared.storage.jsonl import JSONLStorage


@pytest.mark.storage
class TestJSONLStorage:
    """Tests for JSONLStorage backend."""

    def test_jsonl_storage_initialization(self, tmp_path):
        """Test JSONL storage initialization creates file if needed."""
        jsonl_path = tmp_path / "reflections.jsonl"
        storage = JSONLStorage(str(jsonl_path))
        
        assert jsonl_path.exists()
        assert storage.filepath == jsonl_path.resolve()

    def test_jsonl_storage_write(self, tmp_path, sample_reflection):
        """Test writing a reflection to JSONL file."""
        jsonl_path = tmp_path / "reflections.jsonl"
        storage = JSONLStorage(str(jsonl_path))
        
        result = storage.write(sample_reflection)
        assert result is True
        
        # Verify content was written
        with open(jsonl_path, 'r') as f:
            lines = f.readlines()
            assert len(lines) == 1
            written = json.loads(lines[0])
            assert written == sample_reflection

    def test_jsonl_storage_write_multiple(self, tmp_path, sample_reflection):
        """Test writing multiple reflections."""
        jsonl_path = tmp_path / "reflections.jsonl"
        storage = JSONLStorage(str(jsonl_path))
        
        reflection1 = {**sample_reflection, "commit_hash": "abc123"}
        reflection2 = {**sample_reflection, "commit_hash": "def456"}
        
        storage.write(reflection1)
        storage.write(reflection2)
        
        with open(jsonl_path, 'r') as f:
            lines = f.readlines()
            assert len(lines) == 2
            assert json.loads(lines[0])["commit_hash"] == "abc123"
            assert json.loads(lines[1])["commit_hash"] == "def456"

    def test_jsonl_storage_adds_timestamp(self, tmp_path):
        """Test that timestamp is added if missing."""
        jsonl_path = tmp_path / "reflections.jsonl"
        storage = JSONLStorage(str(jsonl_path))
        
        reflection = {"commit_hash": "abc123", "what_changed": "test"}
        result = storage.write(reflection)
        
        assert result is True
        with open(jsonl_path, 'r') as f:
            written = json.loads(f.read().strip())
            assert "timestamp" in written
            assert isinstance(written["timestamp"], str)

    def test_jsonl_storage_read_recent_empty(self, tmp_path):
        """Test reading from empty JSONL file."""
        jsonl_path = tmp_path / "reflections.jsonl"
        storage = JSONLStorage(str(jsonl_path))
        
        reflections = storage.read_recent(limit=10)
        assert reflections == []

    def test_jsonl_storage_read_recent(self, tmp_path, sample_reflection):
        """Test reading recent reflections."""
        jsonl_path = tmp_path / "reflections.jsonl"
        storage = JSONLStorage(str(jsonl_path))
        
        # Write multiple reflections
        for i in range(5):
            ref = {**sample_reflection, "commit_hash": f"hash{i}"}
            storage.write(ref)
        
        # Read recent (should return most recent first)
        reflections = storage.read_recent(limit=3)
        assert len(reflections) == 3
        # Most recent should be last one written
        assert reflections[0]["commit_hash"] == "hash4"

    def test_jsonl_storage_read_recent_with_limit(self, tmp_path, sample_reflection):
        """Test reading with limit."""
        jsonl_path = tmp_path / "reflections.jsonl"
        storage = JSONLStorage(str(jsonl_path))
        
        # Write 10 reflections
        for i in range(10):
            ref = {**sample_reflection, "commit_hash": f"hash{i}"}
            storage.write(ref)
        
        # Read with limit
        reflections = storage.read_recent(limit=5)
        assert len(reflections) == 5

    def test_jsonl_storage_read_recent_with_project_filter(self, tmp_path):
        """Test reading with project filter."""
        jsonl_path = tmp_path / "reflections.jsonl"
        storage = JSONLStorage(str(jsonl_path))
        
        # Write reflections for different projects
        storage.write({"commit_hash": "abc", "project": "project1"})
        storage.write({"commit_hash": "def", "project": "project2"})
        storage.write({"commit_hash": "ghi", "project": "project1"})
        
        # Filter by project
        reflections = storage.read_recent(limit=10, project="project1")
        assert len(reflections) == 2
        assert all(r["project"] == "project1" for r in reflections)

    def test_jsonl_storage_read_recent_with_since_filter(self, tmp_path):
        """Test reading with since timestamp filter."""
        jsonl_path = tmp_path / "reflections.jsonl"
        storage = JSONLStorage(str(jsonl_path))
        
        base_time = datetime.now(timezone.utc)
        
        # Write reflections with different timestamps
        storage.write({
            "commit_hash": "old",
            "timestamp": (base_time.replace(hour=0)).isoformat()
        })
        storage.write({
            "commit_hash": "recent",
            "timestamp": (base_time.replace(hour=12)).isoformat()
        })
        
        # Filter by since time
        since = base_time.replace(hour=6)
        reflections = storage.read_recent(limit=10, since=since)
        assert len(reflections) >= 1
        assert any(r["commit_hash"] == "recent" for r in reflections)

    def test_jsonl_storage_close(self, tmp_path):
        """Test closing storage backend."""
        jsonl_path = tmp_path / "reflections.jsonl"
        storage = JSONLStorage(str(jsonl_path))
        
        # Close should not raise
        storage.close()
        
        # Storage should still be usable after close
        storage.write({"commit_hash": "test"})
        assert True

    def test_jsonl_storage_context_manager(self, tmp_path):
        """Test using storage as context manager."""
        jsonl_path = tmp_path / "reflections.jsonl"
        
        with JSONLStorage(str(jsonl_path)) as storage:
            storage.write({"commit_hash": "test"})
        
        # File should still exist after context exit
        assert jsonl_path.exists()

    def test_jsonl_storage_atomic_write(self, tmp_path, sample_reflection):
        """Test that writes are atomic."""
        jsonl_path = tmp_path / "reflections.jsonl"
        storage = JSONLStorage(str(jsonl_path))
        
        # Write initial reflection
        storage.write(sample_reflection)
        
        # Write another (should be atomic)
        storage.write({**sample_reflection, "commit_hash": "new"})
        
        # File should have both entries, not be corrupted
        with open(jsonl_path, 'r') as f:
            lines = [l for l in f if l.strip()]
            assert len(lines) == 2

    def test_jsonl_storage_handles_invalid_json_gracefully(self, tmp_path):
        """Test that invalid JSON lines are skipped."""
        jsonl_path = tmp_path / "reflections.jsonl"
        storage = JSONLStorage(str(jsonl_path))
        
        # Write valid reflection
        storage.write({"commit_hash": "valid"})
        
        # Manually add invalid line
        with open(jsonl_path, 'a') as f:
            f.write("not valid json\n")
        
        # Should still read valid entries
        reflections = storage.read_recent(limit=10)
        assert len(reflections) == 1
        assert reflections[0]["commit_hash"] == "valid"
