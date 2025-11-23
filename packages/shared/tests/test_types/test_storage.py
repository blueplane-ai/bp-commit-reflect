"""
Unit tests for storage backend abstract interface.

Tests the storage backend interface and contracts.
"""

import pytest
from abc import ABC
from shared.types.storage import StorageBackend, StorageError


class TestStorageBackendInterface:
    """Tests for StorageBackend abstract interface."""

    def test_storage_backend_is_abstract(self):
        """Test that StorageBackend cannot be instantiated directly."""
        with pytest.raises(TypeError):
            StorageBackend()

    def test_storage_backend_requires_implementation(self):
        """Test that concrete implementations must implement all methods."""

        class IncompleteBackend(StorageBackend):
            """Incomplete backend missing required methods."""

            pass

        with pytest.raises(TypeError):
            IncompleteBackend()

    def test_storage_backend_complete_implementation(self):
        """Test that complete implementation can be instantiated."""

        class CompleteBackend(StorageBackend):
            """Complete backend with all required methods."""

            def write(self, reflection):
                return True

            def read(self, limit=None):
                return []

            def read_recent(self, count=10):
                return []

            def health_check(self):
                return True

            def close(self):
                pass

        backend = CompleteBackend()
        assert backend is not None


class TestStorageError:
    """Tests for StorageError exception."""

    def test_storage_error_creation(self):
        """Test creating a storage error."""
        error = StorageError("Test error")
        assert str(error) == "Test error"

    def test_storage_error_with_cause(self):
        """Test storage error with underlying cause."""
        try:
            raise IOError("Disk full")
        except IOError as e:
            error = StorageError("Failed to write", cause=e)
            assert "Failed to write" in str(error)
            assert error.__cause__ == e


class TestMockStorageBackend:
    """Tests using mock storage backend."""

    def test_mock_backend_write(self, mock_storage_backend, sample_reflection):
        """Test write operation with mock backend."""
        result = mock_storage_backend.write(sample_reflection)
        assert result is True
        mock_storage_backend.write.assert_called_once_with(sample_reflection)

    def test_mock_backend_read(self, mock_storage_backend):
        """Test read operation with mock backend."""
        result = mock_storage_backend.read()
        assert result == []
        mock_storage_backend.read.assert_called_once()

    def test_mock_backend_read_recent(self, mock_storage_backend):
        """Test read_recent operation with mock backend."""
        result = mock_storage_backend.read_recent(count=5)
        assert result == []
        mock_storage_backend.read_recent.assert_called_once_with(count=5)

    def test_mock_backend_health_check(self, mock_storage_backend):
        """Test health check operation with mock backend."""
        result = mock_storage_backend.health_check()
        assert result is True
        mock_storage_backend.health_check.assert_called_once()
