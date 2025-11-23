"""
Tests for storage factory and multi-backend coordinator.

Tests the factory pattern for creating storage backends and coordinating
writes across multiple backends.
"""

import pytest
from unittest.mock import Mock, MagicMock

from shared.storage.factory import StorageFactory, MultiBackendCoordinator
from shared.storage.jsonl import JSONLStorage
from shared.storage.sqlite import SQLiteStorage
from shared.types.storage import StorageError, StorageBackend
from shared.types.config import StorageConfig, StorageBackendConfig


@pytest.mark.storage
class TestStorageFactory:
    """Tests for StorageFactory."""

    def test_factory_initialization(self):
        """Test factory initializes with empty registry."""
        factory = StorageFactory()
        assert len(factory.get_registered_types()) == 0

    def test_factory_register_backend(self):
        """Test registering a backend type."""
        factory = StorageFactory()
        
        # Create a mock backend class
        class MockBackend(StorageBackend):
            def initialize(self):
                pass
            def close(self):
                pass
            def save_reflection(self, reflection):
                pass
            def get_reflection(self, reflection_id):
                pass
            def query_reflections(self, options):
                pass
            def delete_reflection(self, reflection_id):
                pass
            def count_reflections(self, filter_by=None):
                pass
            def health_check(self):
                pass
        
        factory.register_backend("mock", MockBackend)
        assert factory.is_registered("mock")
        assert "mock" in factory.get_registered_types()

    def test_factory_register_duplicate_backend(self):
        """Test that registering duplicate backend raises error."""
        factory = StorageFactory()
        
        class MockBackend(StorageBackend):
            def initialize(self):
                pass
            def close(self):
                pass
            def save_reflection(self, reflection):
                pass
            def get_reflection(self, reflection_id):
                pass
            def query_reflections(self, options):
                pass
            def delete_reflection(self, reflection_id):
                pass
            def count_reflections(self, filter_by=None):
                pass
            def health_check(self):
                pass
        
        factory.register_backend("mock", MockBackend)
        
        with pytest.raises(StorageError):
            factory.register_backend("mock", MockBackend)

    def test_factory_register_invalid_backend(self):
        """Test that registering non-Backend class raises error."""
        factory = StorageFactory()
        
        class NotABackend:
            pass
        
        with pytest.raises(StorageError):
            factory.register_backend("invalid", NotABackend)

    def test_factory_create_backend(self, tmp_path):
        """Test creating a backend instance."""
        factory = StorageFactory()
        factory.register_backend("jsonl", JSONLStorage)
        
        config = StorageBackendConfig(
            type="jsonl",
            path=str(tmp_path / "test.jsonl")
        )
        
        backend = factory.create_backend(config)
        assert isinstance(backend, JSONLStorage)

    def test_factory_create_unregistered_backend(self):
        """Test that creating unregistered backend raises error."""
        factory = StorageFactory()
        
        config = StorageBackendConfig(
            type="nonexistent",
            path="/tmp/test"
        )
        
        with pytest.raises(StorageError):
            factory.create_backend(config)

    def test_factory_create_multiple_backends(self, tmp_path):
        """Test creating multiple backends from config."""
        factory = StorageFactory()
        factory.register_backend("jsonl", JSONLStorage)
        
        storage_config = StorageConfig(
            backends=[
                StorageBackendConfig(
                    type="jsonl",
                    path=str(tmp_path / "test1.jsonl")
                ),
                StorageBackendConfig(
                    type="jsonl",
                    path=str(tmp_path / "test2.jsonl")
                ),
            ]
        )
        
        backends = factory.create_backends(storage_config)
        assert len(backends) == 2
        assert all(isinstance(b, JSONLStorage) for b in backends)


@pytest.mark.storage
class TestMultiBackendCoordinator:
    """Tests for MultiBackendCoordinator."""

    def test_coordinator_initialization(self):
        """Test coordinator initialization."""
        mock_backend1 = Mock(spec=StorageBackend)
        mock_backend1.get_type = Mock(return_value="mock1")
        
        coordinator = MultiBackendCoordinator([mock_backend1])
        assert len(coordinator.backends) == 1
        assert coordinator._primary_backend == mock_backend1

    def test_coordinator_requires_at_least_one_backend(self):
        """Test that coordinator requires at least one backend."""
        with pytest.raises(StorageError):
            MultiBackendCoordinator([])

    def test_coordinator_sets_primary_backend(self):
        """Test that primary backend is set correctly."""
        mock_backend1 = Mock(spec=StorageBackend)
        mock_backend1.get_type = Mock(return_value="mock1")
        
        mock_backend2 = Mock(spec=StorageBackend)
        mock_backend2.get_type = Mock(return_value="mock2")
        
        coordinator = MultiBackendCoordinator(
            [mock_backend1, mock_backend2],
            primary_type="mock2"
        )
        assert coordinator._primary_backend == mock_backend2

    def test_coordinator_write_all_backends(self, sample_reflection):
        """Test writing to all backends."""
        mock_backend1 = Mock(spec=StorageBackend)
        mock_backend1.get_type = Mock(return_value="mock1")
        mock_backend1.write = Mock(return_value=True)
        
        mock_backend2 = Mock(spec=StorageBackend)
        mock_backend2.get_type = Mock(return_value="mock2")
        mock_backend2.write = Mock(return_value=True)
        
        coordinator = MultiBackendCoordinator([mock_backend1, mock_backend2])
        
        result = coordinator.write(sample_reflection)
        assert result is True
        mock_backend1.write.assert_called_once_with(sample_reflection)
        mock_backend2.write.assert_called_once_with(sample_reflection)

    def test_coordinator_write_primary_success(self, sample_reflection):
        """Test that primary backend success returns True."""
        mock_backend1 = Mock(spec=StorageBackend)
        mock_backend1.get_type = Mock(return_value="mock1")
        mock_backend1.write = Mock(return_value=True)
        
        mock_backend2 = Mock(spec=StorageBackend)
        mock_backend2.get_type = Mock(return_value="mock2")
        mock_backend2.write = Mock(return_value=False)
        
        coordinator = MultiBackendCoordinator([mock_backend1, mock_backend2])
        
        result = coordinator.write(sample_reflection)
        assert result is True  # Primary succeeded

    def test_coordinator_write_all_fail(self, sample_reflection):
        """Test that all backend failures raise error."""
        mock_backend1 = Mock(spec=StorageBackend)
        mock_backend1.get_type = Mock(return_value="mock1")
        mock_backend1.write = Mock(side_effect=Exception("Error 1"))
        
        mock_backend2 = Mock(spec=StorageBackend)
        mock_backend2.get_type = Mock(return_value="mock2")
        mock_backend2.write = Mock(side_effect=Exception("Error 2"))
        
        coordinator = MultiBackendCoordinator([mock_backend1, mock_backend2])
        
        with pytest.raises(StorageError):
            coordinator.write(sample_reflection)

    def test_coordinator_read_primary_backend(self):
        """Test reading from primary backend."""
        mock_backend1 = Mock(spec=StorageBackend)
        mock_backend1.get_type = Mock(return_value="mock1")
        mock_backend1.read = Mock(return_value=[{"test": "data"}])
        
        mock_backend2 = Mock(spec=StorageBackend)
        mock_backend2.get_type = Mock(return_value="mock2")
        
        coordinator = MultiBackendCoordinator([mock_backend1, mock_backend2])
        
        result = coordinator.read(limit=10)
        assert result == [{"test": "data"}]
        mock_backend1.read.assert_called_once_with(limit=10)

    def test_coordinator_read_fallback(self):
        """Test reading falls back to other backends if primary fails."""
        mock_backend1 = Mock(spec=StorageBackend)
        mock_backend1.get_type = Mock(return_value="mock1")
        mock_backend1.read = Mock(side_effect=Exception("Error"))
        
        mock_backend2 = Mock(spec=StorageBackend)
        mock_backend2.get_type = Mock(return_value="mock2")
        mock_backend2.read = Mock(return_value=[{"test": "data"}])
        
        coordinator = MultiBackendCoordinator([mock_backend1, mock_backend2])
        
        result = coordinator.read(limit=10)
        assert result == [{"test": "data"}]
        mock_backend2.read.assert_called_once_with(limit=10)

    def test_coordinator_read_recent(self):
        """Test read_recent method."""
        mock_backend1 = Mock(spec=StorageBackend)
        mock_backend1.get_type = Mock(return_value="mock1")
        mock_backend1.read_recent = Mock(return_value=[{"test": "data"}])
        
        coordinator = MultiBackendCoordinator([mock_backend1])
        
        result = coordinator.read_recent(count=5)
        assert result == [{"test": "data"}]
        mock_backend1.read_recent.assert_called_once_with(count=5)

    def test_coordinator_health_check(self):
        """Test health check across all backends."""
        mock_backend1 = Mock(spec=StorageBackend)
        mock_backend1.get_type = Mock(return_value="mock1")
        mock_backend1.health_check = Mock(return_value=True)
        
        mock_backend2 = Mock(spec=StorageBackend)
        mock_backend2.get_type = Mock(return_value="mock2")
        mock_backend2.health_check = Mock(return_value=False)
        
        coordinator = MultiBackendCoordinator([mock_backend1, mock_backend2])
        
        health = coordinator.health_check()
        assert health["mock1"] is True
        assert health["mock2"] is False

    def test_coordinator_get_healthy_backends(self):
        """Test getting only healthy backends."""
        mock_backend1 = Mock(spec=StorageBackend)
        mock_backend1.get_type = Mock(return_value="mock1")
        mock_backend1.health_check = Mock(return_value=True)
        
        mock_backend2 = Mock(spec=StorageBackend)
        mock_backend2.get_type = Mock(return_value="mock2")
        mock_backend2.health_check = Mock(return_value=False)
        
        coordinator = MultiBackendCoordinator([mock_backend1, mock_backend2])
        
        healthy = coordinator.get_healthy_backends()
        assert len(healthy) == 1
        assert healthy[0] == mock_backend1

    def test_coordinator_close_all(self):
        """Test closing all backends."""
        mock_backend1 = Mock(spec=StorageBackend)
        mock_backend1.get_type = Mock(return_value="mock1")
        mock_backend1.close = Mock()
        
        mock_backend2 = Mock(spec=StorageBackend)
        mock_backend2.get_type = Mock(return_value="mock2")
        mock_backend2.close = Mock()
        
        coordinator = MultiBackendCoordinator([mock_backend1, mock_backend2])
        coordinator.close_all()
        
        mock_backend1.close.assert_called_once()
        mock_backend2.close.assert_called_once()
