"""Commit queue for managing pending reflection requests."""

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class QueuedCommit:
    """A commit waiting for reflection."""

    commit_hash: str
    project: str
    branch: str
    repo_path: str | None = None  # Path to the git repository
    received_at: datetime = field(default_factory=datetime.now)

    @property
    def short_hash(self) -> str:
        """Return first 7 characters of commit hash."""
        return self.commit_hash[:7] if self.commit_hash else ""

    def __repr__(self) -> str:
        return f"QueuedCommit({self.short_hash}, {self.project}/{self.branch})"


class CommitQueue:
    """Thread-safe queue for pending commits awaiting reflection.

    Manages a FIFO queue of commits that have been detected but not yet
    processed. Also tracks the "current" commit being actively reflected on.
    """

    def __init__(self, max_size: int = 100):
        """Initialize the commit queue.

        Args:
            max_size: Maximum number of commits to queue (oldest dropped if exceeded)
        """
        self._queue: deque[QueuedCommit] = deque(maxlen=max_size)
        self._current: QueuedCommit | None = None
        self._max_size = max_size

    def enqueue(self, commit: QueuedCommit) -> int:
        """Add a commit to the queue.

        Args:
            commit: The commit to queue

        Returns:
            Current queue size after adding
        """
        self._queue.append(commit)
        return len(self._queue)

    def dequeue(self) -> QueuedCommit | None:
        """Get and remove the next commit from the queue.

        Also sets this commit as the "current" commit being processed.

        Returns:
            The next commit, or None if queue is empty
        """
        if self._queue:
            self._current = self._queue.popleft()
            return self._current
        return None

    def peek(self) -> QueuedCommit | None:
        """Look at the next commit without removing it.

        Returns:
            The next commit, or None if queue is empty
        """
        return self._queue[0] if self._queue else None

    @property
    def size(self) -> int:
        """Current number of commits in queue."""
        return len(self._queue)

    @property
    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return len(self._queue) == 0

    @property
    def current(self) -> QueuedCommit | None:
        """The commit currently being processed (if any)."""
        return self._current

    def clear_current(self) -> None:
        """Clear the current commit reference.

        Call this after finishing or cancelling a reflection.
        """
        self._current = None

    def get_all(self) -> list[QueuedCommit]:
        """Get all queued commits (for display purposes).

        Returns:
            List of all commits in queue order (does not modify queue)
        """
        return list(self._queue)

    def clear(self) -> int:
        """Clear all commits from the queue.

        Returns:
            Number of commits that were cleared
        """
        count = len(self._queue)
        self._queue.clear()
        self._current = None
        return count

    def __len__(self) -> int:
        """Return queue size."""
        return len(self._queue)

    def __bool__(self) -> bool:
        """Return True if queue has items."""
        return len(self._queue) > 0

    def __repr__(self) -> str:
        current_info = f", current={self._current.short_hash}" if self._current else ""
        return f"CommitQueue(size={self.size}{current_info})"
