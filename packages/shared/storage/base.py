"""Base storage backend interface."""

from abc import ABC, abstractmethod
from datetime import datetime
from types import TracebackType
from typing import Any, Optional

from typing_extensions import Self


class StorageBackend(ABC):
    """Abstract base class for storage backends."""

    @abstractmethod
    def write(self, reflection: dict[str, Any]) -> bool:
        """
        Write a reflection to storage.

        Args:
            reflection: Complete reflection data

        Returns:
            True if write succeeded, False otherwise
        """
        pass

    @abstractmethod
    def read_recent(
        self, limit: int = 10, project: Optional[str] = None, since: Optional[datetime] = None
    ) -> list[dict[str, Any]]:
        """
        Read recent reflections from storage.

        Args:
            limit: Maximum number of reflections to return
            project: Filter by project name (optional)
            since: Filter reflections since this timestamp (optional)

        Returns:
            List of reflection dictionaries
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """Close the storage backend and clean up resources."""
        pass

    def __enter__(self) -> Self:
        """Context manager entry."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Context manager exit."""
        self.close()
