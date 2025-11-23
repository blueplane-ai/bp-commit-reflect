"""
Storage factory for creating and managing storage backends.

This module implements the factory pattern for creating storage backends
based on configuration, supporting multiple backend types and coordinating
writes across multiple backends.
"""

from typing import Dict, List, Optional, Type
from shared.types.storage import StorageBackend, StorageError
from shared.types.config import StorageConfig, StorageBackendConfig


class StorageFactory:
    """
    Factory for creating storage backend instances.

    Manages registration of backend types and creates instances
    based on configuration.
    """

    def __init__(self):
        """Initialize the storage factory with empty backend registry."""
        self._backends: Dict[str, Type[StorageBackend]] = {}

    def register_backend(
        self, backend_type: str, backend_class: Type[StorageBackend]
    ) -> None:
        """
        Register a storage backend type.

        Args:
            backend_type: Type identifier (e.g., "jsonl", "sqlite")
            backend_class: Backend class to instantiate

        Raises:
            StorageError: If backend type already registered
        """
        if backend_type in self._backends:
            raise StorageError(
                f"Backend type '{backend_type}' is already registered"
            )

        if not issubclass(backend_class, StorageBackend):
            raise StorageError(
                f"Backend class must inherit from StorageBackend, got {backend_class}"
            )

        self._backends[backend_type] = backend_class

    def create_backend(self, config: StorageBackendConfig) -> StorageBackend:
        """
        Create a storage backend instance from configuration.

        Args:
            config: Backend configuration

        Returns:
            Initialized storage backend instance

        Raises:
            StorageError: If backend type not registered or creation fails
        """
        backend_type = config.type

        if backend_type not in self._backends:
            raise StorageError(
                f"Unknown backend type '{backend_type}'. "
                f"Available types: {list(self._backends.keys())}"
            )

        backend_class = self._backends[backend_type]

        try:
            backend = backend_class(config)
            return backend
        except Exception as e:
            raise StorageError(
                f"Failed to create backend '{backend_type}': {str(e)}"
            ) from e

    def create_backends(
        self, storage_config: StorageConfig
    ) -> List[StorageBackend]:
        """
        Create multiple backend instances from storage configuration.

        Args:
            storage_config: Storage configuration with multiple backends

        Returns:
            List of initialized backend instances

        Raises:
            StorageError: If any backend creation fails
        """
        backends = []

        for backend_config in storage_config.backends:
            backend = self.create_backend(backend_config)
            backends.append(backend)

        return backends

    def get_registered_types(self) -> List[str]:
        """
        Get list of registered backend types.

        Returns:
            List of backend type identifiers
        """
        return list(self._backends.keys())

    def is_registered(self, backend_type: str) -> bool:
        """
        Check if a backend type is registered.

        Args:
            backend_type: Type identifier to check

        Returns:
            True if registered, False otherwise
        """
        return backend_type in self._backends


class MultiBackendCoordinator:
    """
    Coordinates writes and reads across multiple storage backends.

    Manages primary/fallback logic, parallel writes, and read prioritization.
    """

    def __init__(
        self,
        backends: List[StorageBackend],
        primary_type: Optional[str] = None,
    ):
        """
        Initialize coordinator with backend instances.

        Args:
            backends: List of storage backend instances
            primary_type: Optional primary backend type for reads
        """
        if not backends:
            raise StorageError("At least one backend is required")

        self.backends = backends
        self.primary_type = primary_type
        self._primary_backend = self._find_primary_backend()

    def _find_primary_backend(self) -> Optional[StorageBackend]:
        """Find the primary backend based on type preference."""
        if not self.primary_type:
            # Default to first backend
            return self.backends[0]

        for backend in self.backends:
            if backend.get_type() == self.primary_type:
                return backend

        # Primary type not found, use first backend
        return self.backends[0]

    def write(self, reflection: Dict) -> bool:
        """
        Write reflection to all backends.

        Writes to all backends in parallel. Returns True if at least
        the primary backend succeeds.

        Args:
            reflection: Reflection data to write

        Returns:
            True if primary backend write succeeded

        Raises:
            StorageError: If all backends fail
        """
        results = []
        errors = []

        for backend in self.backends:
            try:
                result = backend.write(reflection)
                results.append((backend, result))
            except Exception as e:
                errors.append((backend, e))
                results.append((backend, False))

        # Check if primary backend succeeded
        primary_success = False
        if self._primary_backend:
            for backend, result in results:
                if backend == self._primary_backend:
                    primary_success = result
                    break

        # If all failed, raise error
        if not any(result for _, result in results):
            error_details = [
                f"{backend.get_type()}: {str(error)}"
                for backend, error in errors
            ]
            raise StorageError(
                f"All storage backends failed: {'; '.join(error_details)}"
            )

        return primary_success

    def read(self, limit: Optional[int] = None) -> List[Dict]:
        """
        Read reflections from primary backend.

        Falls back to other backends if primary fails.

        Args:
            limit: Optional limit on number of records

        Returns:
            List of reflection records

        Raises:
            StorageError: If all backends fail
        """
        # Try primary backend first
        if self._primary_backend:
            try:
                return self._primary_backend.read(limit=limit)
            except Exception:
                pass  # Fall back to other backends

        # Try remaining backends in order
        for backend in self.backends:
            if backend == self._primary_backend:
                continue

            try:
                return backend.read(limit=limit)
            except Exception:
                continue

        raise StorageError("All storage backends failed to read data")

    def read_recent(self, count: int = 10) -> List[Dict]:
        """
        Read recent reflections from primary backend.

        Args:
            count: Number of recent records to retrieve

        Returns:
            List of recent reflection records

        Raises:
            StorageError: If all backends fail
        """
        # Try primary backend first
        if self._primary_backend:
            try:
                return self._primary_backend.read_recent(count=count)
            except Exception:
                pass

        # Try remaining backends
        for backend in self.backends:
            if backend == self._primary_backend:
                continue

            try:
                return backend.read_recent(count=count)
            except Exception:
                continue

        raise StorageError("All storage backends failed to read recent data")

    def health_check(self) -> Dict[str, bool]:
        """
        Check health status of all backends.

        Returns:
            Dictionary mapping backend type to health status
        """
        health_status = {}

        for backend in self.backends:
            backend_type = backend.get_type()
            try:
                is_healthy = backend.health_check()
                health_status[backend_type] = is_healthy
            except Exception:
                health_status[backend_type] = False

        return health_status

    def get_healthy_backends(self) -> List[StorageBackend]:
        """
        Get list of backends that pass health check.

        Returns:
            List of healthy backend instances
        """
        healthy = []

        for backend in self.backends:
            try:
                if backend.health_check():
                    healthy.append(backend)
            except Exception:
                continue

        return healthy

    def close_all(self) -> None:
        """Close all backend connections."""
        for backend in self.backends:
            try:
                backend.close()
            except Exception:
                pass  # Best effort cleanup


# Global factory instance
_default_factory = StorageFactory()


def get_default_factory() -> StorageFactory:
    """
    Get the default global storage factory.

    Returns:
        Global storage factory instance
    """
    return _default_factory


def register_backend(
    backend_type: str, backend_class: Type[StorageBackend]
) -> None:
    """
    Register a backend with the default factory.

    Args:
        backend_type: Type identifier
        backend_class: Backend class
    """
    _default_factory.register_backend(backend_type, backend_class)
