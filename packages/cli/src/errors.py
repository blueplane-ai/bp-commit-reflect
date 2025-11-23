"""Error handling and recovery mechanisms."""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


class SessionError(Exception):
    """Base exception for session-related errors."""
    pass


class StorageError(Exception):
    """Exception for storage operation failures."""
    pass


class ConfigurationError(Exception):
    """Exception for configuration errors."""
    pass


class RecoveryManager:
    """
    Manages error recovery for partial sessions.

    Saves session state to allow recovery after crashes or interruptions.
    """

    def __init__(self, recovery_dir: str = "~/.commit-reflect/recovery"):
        """
        Initialize recovery manager.

        Args:
            recovery_dir: Directory to store recovery files
        """
        self.recovery_dir = Path(recovery_dir).expanduser()
        self.recovery_dir.mkdir(parents=True, exist_ok=True)

    def save_session_state(self, session_id: str, state: Dict[str, Any]) -> bool:
        """
        Save session state for recovery.

        Args:
            session_id: Unique session identifier
            state: Session state dictionary

        Returns:
            True if save succeeded, False otherwise
        """
        try:
            recovery_file = self.recovery_dir / f"{session_id}.json"
            state_with_timestamp = {
                **state,
                "saved_at": datetime.utcnow().isoformat() + "Z"
            }

            with open(recovery_file, "w", encoding="utf-8") as f:
                json.dump(state_with_timestamp, f, indent=2)

            return True

        except Exception as e:
            print(f"Warning: Failed to save recovery state: {e}")
            return False

    def load_session_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Load saved session state.

        Args:
            session_id: Unique session identifier

        Returns:
            Session state dictionary, or None if not found
        """
        try:
            recovery_file = self.recovery_dir / f"{session_id}.json"

            if not recovery_file.exists():
                return None

            with open(recovery_file, "r", encoding="utf-8") as f:
                state = json.load(f)

            return state

        except Exception as e:
            print(f"Warning: Failed to load recovery state: {e}")
            return None

    def clear_session_state(self, session_id: str) -> bool:
        """
        Clear saved session state after successful completion.

        Args:
            session_id: Unique session identifier

        Returns:
            True if clear succeeded, False otherwise
        """
        try:
            recovery_file = self.recovery_dir / f"{session_id}.json"

            if recovery_file.exists():
                recovery_file.unlink()

            return True

        except Exception as e:
            print(f"Warning: Failed to clear recovery state: {e}")
            return False

    def list_recoverable_sessions(self) -> list:
        """
        List all sessions that have saved recovery state.

        Returns:
            List of tuples: (session_id, saved_timestamp, state_summary)
        """
        sessions = []

        try:
            for recovery_file in self.recovery_dir.glob("*.json"):
                try:
                    with open(recovery_file, "r", encoding="utf-8") as f:
                        state = json.load(f)

                    session_id = recovery_file.stem
                    saved_at = state.get("saved_at", "unknown")
                    summary = {
                        "project": state.get("project", "unknown"),
                        "commit": state.get("commit_hash", "unknown")[:8],
                        "questions_answered": len(state.get("answers", {}))
                    }

                    sessions.append((session_id, saved_at, summary))

                except Exception:
                    continue

            # Sort by timestamp, most recent first
            sessions.sort(key=lambda x: x[1], reverse=True)

        except Exception as e:
            print(f"Warning: Failed to list recoverable sessions: {e}")

        return sessions


def handle_storage_failure(
    backends: list,
    reflection: Dict[str, Any],
    min_success: int = 1
) -> Tuple[list, list]:
    """
    Gracefully handle storage failures across multiple backends.

    Args:
        backends: List of storage backend instances
        reflection: Reflection data to store
        min_success: Minimum number of successful writes required

    Returns:
        Tuple of (successful_backends, failed_backends)

    Raises:
        StorageError: If fewer than min_success backends succeed
    """
    successful = []
    failed = []

    for backend in backends:
        try:
            if backend.write(reflection):
                successful.append(backend)
            else:
                failed.append((backend, "Write returned False"))
        except Exception as e:
            failed.append((backend, str(e)))

    if len(successful) < min_success:
        raise StorageError(
            f"Failed to write to minimum required backends. "
            f"Successful: {len(successful)}, Required: {min_success}"
        )

    if failed:
        print(f"Warning: {len(failed)} storage backend(s) failed:")
        for backend, error in failed:
            print(f"  - {backend}: {error}")

    return successful, failed
