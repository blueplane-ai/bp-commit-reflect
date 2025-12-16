"""JSONL storage backend implementation."""

import fcntl
import json
import os
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .base import StorageBackend


class JSONLStorage(StorageBackend):
    """
    JSONL (JSON Lines) storage backend.

    Features:
    - Atomic write operations
    - Append-only log handling
    - File locking for concurrent access safety
    - Efficient read operations for historical data
    """

    def __init__(self, filepath: str):
        """
        Initialize JSONL storage.

        Args:
            filepath: Path to the JSONL file
        """
        self.filepath = Path(filepath).expanduser().resolve()
        self._ensure_file_exists()

    def _ensure_file_exists(self) -> None:
        """Ensure the JSONL file and parent directories exist."""
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        if not self.filepath.exists():
            self.filepath.touch()

    @contextmanager
    def _lock_file(self, file_handle, operation):
        """
        Context manager for file locking.

        Args:
            file_handle: Open file handle
            operation: fcntl lock operation (LOCK_SH or LOCK_EX)
        """
        try:
            fcntl.flock(file_handle.fileno(), operation)
            yield
        finally:
            fcntl.flock(file_handle.fileno(), fcntl.LOCK_UN)

    def write(self, reflection: dict[str, Any]) -> bool:
        """
        Write a reflection to the JSONL file atomically.

        Uses file locking to prevent concurrent write conflicts.
        Writes to a temporary file first, then atomically renames.

        Args:
            reflection: Complete reflection data

        Returns:
            True if write succeeded, False otherwise
        """
        try:
            # Add timestamp if not present
            if "timestamp" not in reflection:
                reflection["timestamp"] = datetime.utcnow().isoformat() + "Z"

            # Create temporary file in same directory for atomic rename
            temp_path = self.filepath.with_suffix(".jsonl.tmp")

            # Read existing content with shared lock
            existing_lines = []
            if self.filepath.exists() and self.filepath.stat().st_size > 0:
                with open(self.filepath, encoding="utf-8") as f:
                    with self._lock_file(f, fcntl.LOCK_SH):
                        existing_lines = f.readlines()

            # Write all content to temporary file with exclusive lock
            with open(temp_path, "w", encoding="utf-8") as f:
                with self._lock_file(f, fcntl.LOCK_EX):
                    # Write existing lines
                    for line in existing_lines:
                        f.write(line)

                    # Append new reflection
                    json.dump(reflection, f, ensure_ascii=False)
                    f.write("\n")
                    f.flush()
                    os.fsync(f.fileno())  # Ensure data is written to disk

            # Atomic rename
            temp_path.replace(self.filepath)

            return True

        except Exception as e:
            print(f"Error writing to JSONL: {e}")
            # Clean up temporary file if it exists
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass
            return False

    def read_recent(
        self, limit: int = 10, project: Optional[str] = None, since: Optional[datetime] = None
    ) -> list[dict[str, Any]]:
        """
        Read recent reflections from the JSONL file.

        Args:
            limit: Maximum number of reflections to return
            project: Filter by project name (optional)
            since: Filter reflections since this timestamp (optional)

        Returns:
            List of reflection dictionaries, most recent first
        """
        if not self.filepath.exists():
            return []

        reflections = []

        try:
            with open(self.filepath, encoding="utf-8") as f:
                with self._lock_file(f, fcntl.LOCK_SH):
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue

                        try:
                            reflection = json.loads(line)

                            # Apply filters
                            if project and reflection.get("project") != project:
                                continue

                            if since:
                                timestamp_str = reflection.get("timestamp", "")
                                try:
                                    # Parse ISO format timestamp
                                    timestamp = datetime.fromisoformat(
                                        timestamp_str.replace("Z", "+00:00")
                                    )
                                    if timestamp < since:
                                        continue
                                except (ValueError, AttributeError):
                                    continue

                            reflections.append(reflection)

                        except json.JSONDecodeError:
                            # Skip malformed lines
                            continue

            # Return most recent first, limited to requested count
            return reflections[-limit:][::-1]

        except Exception as e:
            print(f"Error reading from JSONL: {e}")
            return []

    def read_all(self) -> list[dict[str, Any]]:
        """
        Read all reflections from the JSONL file.

        Returns:
            List of all reflection dictionaries
        """
        return self.read_recent(limit=float("inf"))

    def close(self) -> None:
        """Close the storage backend (no-op for JSONL)."""
        pass

    def __repr__(self) -> str:
        return f"JSONLStorage(filepath='{self.filepath}')"
