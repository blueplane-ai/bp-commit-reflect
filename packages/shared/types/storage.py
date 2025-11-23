"""
Storage backend interfaces for the Commit Reflection System.

This module defines abstract interfaces that all storage backends must
implement, ensuring consistent behavior across different storage types.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from uuid import UUID

from .reflection import Reflection


class StorageError(Exception):
    """Base exception for storage-related errors."""
    pass


class StorageConnectionError(StorageError):
    """Error connecting to storage backend."""
    pass


class StorageWriteError(StorageError):
    """Error writing to storage backend."""
    pass


class StorageReadError(StorageError):
    """Error reading from storage backend."""
    pass


class StorageValidationError(StorageError):
    """Error validating data for storage."""
    pass


class SortOrder(str, Enum):
    """Sort order for query results."""
    ASC = "asc"
    DESC = "desc"


@dataclass
class QueryOptions:
    """
    Options for querying reflections from storage.

    Attributes:
        limit: Maximum number of results to return
        offset: Number of results to skip
        sort_by: Field to sort by
        sort_order: Sort order (ascending or descending)
        filter_by: Dictionary of field filters
        date_from: Filter reflections from this date
        date_to: Filter reflections until this date
        project_name: Filter by project name
        branch: Filter by branch name
        author_email: Filter by author email
    """
    limit: Optional[int] = None
    offset: int = 0
    sort_by: str = "created_at"
    sort_order: SortOrder = SortOrder.DESC
    filter_by: Optional[Dict[str, Any]] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    project_name: Optional[str] = None
    branch: Optional[str] = None
    author_email: Optional[str] = None

    def __post_init__(self):
        """Validate query options."""
        if isinstance(self.sort_order, str):
            self.sort_order = SortOrder(self.sort_order)

        if self.limit is not None and self.limit < 1:
            raise ValueError("Limit must be positive")

        if self.offset < 0:
            raise ValueError("Offset must be non-negative")


@dataclass
class StorageResult:
    """
    Result of a storage operation.

    Attributes:
        success: Whether the operation succeeded
        message: Optional message about the operation
        data: Optional data returned from the operation
        error: Optional error if operation failed
    """
    success: bool
    message: Optional[str] = None
    data: Optional[Any] = None
    error: Optional[Exception] = None

    @classmethod
    def success_result(cls, message: str = "Operation successful", data: Any = None) -> "StorageResult":
        """Create a successful result."""
        return cls(success=True, message=message, data=data)

    @classmethod
    def error_result(cls, message: str, error: Optional[Exception] = None) -> "StorageResult":
        """Create an error result."""
        return cls(success=False, message=message, error=error)


class StorageBackend(ABC):
    """
    Abstract base class for storage backends.

    All storage implementations must inherit from this class and implement
    its abstract methods to ensure consistent behavior.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the storage backend.

        Args:
            config: Backend-specific configuration
        """
        self.config = config
        self._initialized = False

    @abstractmethod
    def initialize(self) -> StorageResult:
        """
        Initialize the storage backend.

        This may involve creating directories, database connections,
        schema setup, etc.

        Returns:
            StorageResult indicating success or failure
        """
        pass

    @abstractmethod
    def close(self) -> StorageResult:
        """
        Close the storage backend and clean up resources.

        Returns:
            StorageResult indicating success or failure
        """
        pass

    @abstractmethod
    def save_reflection(self, reflection: Reflection) -> StorageResult:
        """
        Save a reflection to storage.

        If a reflection with the same ID exists, it should be updated.

        Args:
            reflection: The reflection to save

        Returns:
            StorageResult indicating success or failure
        """
        pass

    @abstractmethod
    def get_reflection(self, reflection_id: UUID) -> Optional[Reflection]:
        """
        Retrieve a reflection by ID.

        Args:
            reflection_id: UUID of the reflection to retrieve

        Returns:
            The reflection if found, None otherwise

        Raises:
            StorageReadError: If there's an error reading from storage
        """
        pass

    @abstractmethod
    def query_reflections(self, options: QueryOptions) -> List[Reflection]:
        """
        Query reflections based on options.

        Args:
            options: Query options for filtering and sorting

        Returns:
            List of reflections matching the query

        Raises:
            StorageReadError: If there's an error reading from storage
        """
        pass

    @abstractmethod
    def delete_reflection(self, reflection_id: UUID) -> StorageResult:
        """
        Delete a reflection from storage.

        Args:
            reflection_id: UUID of the reflection to delete

        Returns:
            StorageResult indicating success or failure
        """
        pass

    @abstractmethod
    def count_reflections(self, filter_by: Optional[Dict[str, Any]] = None) -> int:
        """
        Count reflections matching optional filters.

        Args:
            filter_by: Optional filters to apply

        Returns:
            Number of reflections matching filters

        Raises:
            StorageReadError: If there's an error reading from storage
        """
        pass

    @abstractmethod
    def health_check(self) -> StorageResult:
        """
        Check if the storage backend is healthy and accessible.

        Returns:
            StorageResult indicating health status
        """
        pass

    def is_initialized(self) -> bool:
        """Check if the backend has been initialized."""
        return self._initialized

    def validate_reflection(self, reflection: Reflection) -> tuple[bool, Optional[str]]:
        """
        Validate a reflection before saving.

        Args:
            reflection: The reflection to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check required fields
        if reflection.id is None:
            return False, "Reflection ID is required"

        if not reflection.answers:
            return False, "Reflection must have at least one answer"

        if reflection.commit_context is None:
            return False, "Commit context is required"

        if reflection.session_metadata is None:
            return False, "Session metadata is required"

        # Validate commit context
        ctx = reflection.commit_context
        if not ctx.commit_hash:
            return False, "Commit hash is required"
        if not ctx.branch:
            return False, "Branch name is required"

        # Validate answers
        for answer in reflection.answers:
            if not answer.question_id:
                return False, "Answer missing question_id"
            if answer.answer is None or answer.answer == "":
                return False, f"Answer for question {answer.question_id} is empty"

        return True, None

    def get_recent_reflections(
        self,
        limit: int = 10,
        project_name: Optional[str] = None
    ) -> List[Reflection]:
        """
        Get the most recent reflections.

        Args:
            limit: Maximum number of reflections to return
            project_name: Optional project name filter

        Returns:
            List of recent reflections
        """
        options = QueryOptions(
            limit=limit,
            sort_by="created_at",
            sort_order=SortOrder.DESC,
            project_name=project_name,
        )
        return self.query_reflections(options)

    def get_reflections_by_commit(self, commit_hash: str) -> List[Reflection]:
        """
        Get all reflections for a specific commit.

        Args:
            commit_hash: The commit hash to search for

        Returns:
            List of reflections for that commit
        """
        options = QueryOptions(
            filter_by={"commit_hash": commit_hash},
            sort_by="created_at",
            sort_order=SortOrder.DESC,
        )
        return self.query_reflections(options)

    def get_reflections_by_date_range(
        self,
        date_from: datetime,
        date_to: datetime,
        project_name: Optional[str] = None
    ) -> List[Reflection]:
        """
        Get reflections within a date range.

        Args:
            date_from: Start date
            date_to: End date
            project_name: Optional project name filter

        Returns:
            List of reflections in date range
        """
        options = QueryOptions(
            date_from=date_from,
            date_to=date_to,
            project_name=project_name,
            sort_by="created_at",
            sort_order=SortOrder.DESC,
        )
        return self.query_reflections(options)


class MultiBackendStorage:
    """
    Coordinator for multiple storage backends.

    Manages writing to multiple backends and reading with fallback logic.
    """

    def __init__(self, backends: List[StorageBackend]):
        """
        Initialize multi-backend storage.

        Args:
            backends: List of storage backends (ordered by priority)
        """
        self.backends = backends

    def initialize_all(self) -> Dict[str, StorageResult]:
        """
        Initialize all backends.

        Returns:
            Dictionary mapping backend names to initialization results
        """
        results = {}
        for i, backend in enumerate(self.backends):
            backend_name = f"{backend.__class__.__name__}_{i}"
            results[backend_name] = backend.initialize()
        return results

    def save_to_all(self, reflection: Reflection) -> Dict[str, StorageResult]:
        """
        Save reflection to all backends.

        Args:
            reflection: The reflection to save

        Returns:
            Dictionary mapping backend names to save results
        """
        results = {}
        for i, backend in enumerate(self.backends):
            backend_name = f"{backend.__class__.__name__}_{i}"
            try:
                results[backend_name] = backend.save_reflection(reflection)
            except Exception as e:
                results[backend_name] = StorageResult.error_result(
                    f"Error saving to {backend_name}",
                    error=e
                )
        return results

    def get_reflection(self, reflection_id: UUID) -> Optional[Reflection]:
        """
        Get reflection from first available backend.

        Tries backends in priority order until one succeeds.

        Args:
            reflection_id: UUID of reflection to retrieve

        Returns:
            The reflection if found in any backend, None otherwise
        """
        for backend in self.backends:
            try:
                reflection = backend.get_reflection(reflection_id)
                if reflection:
                    return reflection
            except StorageReadError:
                continue  # Try next backend
        return None

    def close_all(self) -> Dict[str, StorageResult]:
        """
        Close all backends.

        Returns:
            Dictionary mapping backend names to close results
        """
        results = {}
        for i, backend in enumerate(self.backends):
            backend_name = f"{backend.__class__.__name__}_{i}"
            results[backend_name] = backend.close()
        return results
