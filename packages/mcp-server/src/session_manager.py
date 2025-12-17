"""
Session manager for coordinating CLI process sessions.

Manages the lifecycle of reflection sessions, including creation,
tracking, timeout handling, and cleanup.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


class SessionState(str, Enum):
    """States a reflection session can be in."""

    INITIALIZING = "initializing"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"
    ERROR = "error"


@dataclass
class Session:
    """
    Represents a single reflection session.

    Attributes:
        session_id: Unique identifier for the session
        state: Current state of the session
        created_at: When the session was created
        last_activity: Last time there was activity on this session
        commit_hash: The commit being reflected upon
        project_name: Name of the project
        cli_process: Reference to the CLI subprocess
        current_question_index: Current question being answered
        timeout_seconds: Session timeout in seconds
        metadata: Additional session metadata
    """

    session_id: UUID
    state: SessionState
    created_at: datetime
    last_activity: datetime
    commit_hash: str | None = None
    project_name: str | None = None
    cli_process: asyncio.subprocess.Process | None = None
    current_question_index: int = 0
    timeout_seconds: int = 1800  # 30 minutes default
    metadata: dict[str, Any] = field(default_factory=dict)

    def update_activity(self):
        """Update the last activity timestamp."""
        self.last_activity = datetime.now()

    def is_timed_out(self) -> bool:
        """Check if the session has timed out."""
        if self.state in (SessionState.COMPLETED, SessionState.CANCELLED, SessionState.TIMED_OUT):
            return False

        timeout_threshold = self.last_activity + timedelta(seconds=self.timeout_seconds)
        return datetime.now() > timeout_threshold

    def is_active(self) -> bool:
        """Check if the session is in an active state."""
        return self.state in (SessionState.INITIALIZING, SessionState.ACTIVE)

    def to_dict(self) -> dict[str, Any]:
        """Convert session to dictionary representation."""
        return {
            "session_id": str(self.session_id),
            "state": self.state.value,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "commit_hash": self.commit_hash,
            "project_name": self.project_name,
            "current_question_index": self.current_question_index,
            "timeout_seconds": self.timeout_seconds,
            "metadata": self.metadata,
        }


class SessionManager:
    """
    Manages multiple concurrent reflection sessions.

    Handles session creation, tracking, timeout cleanup, and limits on
    concurrent sessions.
    """

    def __init__(
        self,
        max_concurrent_sessions: int = 10,
        default_timeout: int = 1800,
        cleanup_interval: int = 300,
    ):
        """
        Initialize the session manager.

        Args:
            max_concurrent_sessions: Maximum number of concurrent active sessions
            default_timeout: Default session timeout in seconds
            cleanup_interval: How often to run cleanup in seconds
        """
        self.max_concurrent_sessions = max_concurrent_sessions
        self.default_timeout = default_timeout
        self.cleanup_interval = cleanup_interval

        self.sessions: dict[UUID, Session] = {}
        self._cleanup_task: asyncio.Task | None = None
        self._running = False

    async def start(self):
        """Start the session manager and cleanup task."""
        if self._running:
            logger.warning("Session manager already running")
            return

        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Session manager started")

    async def stop(self):
        """Stop the session manager and cleanup all sessions."""
        if not self._running:
            return

        self._running = False

        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # Cleanup all sessions
        await self._cleanup_all_sessions()
        logger.info("Session manager stopped")

    async def create_session(
        self,
        commit_hash: str,
        project_name: str | None = None,
        timeout_seconds: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Session:
        """
        Create a new reflection session.

        Args:
            commit_hash: The commit hash being reflected upon
            project_name: Optional project name
            timeout_seconds: Optional custom timeout
            metadata: Optional session metadata

        Returns:
            New Session object

        Raises:
            RuntimeError: If max concurrent sessions reached
        """
        # Check concurrent session limit
        active_count = len([s for s in self.sessions.values() if s.is_active()])
        if active_count >= self.max_concurrent_sessions:
            raise RuntimeError(
                f"Maximum concurrent sessions ({self.max_concurrent_sessions}) reached"
            )

        # Create new session
        session_id = uuid4()
        now = datetime.now()

        session = Session(
            session_id=session_id,
            state=SessionState.INITIALIZING,
            created_at=now,
            last_activity=now,
            commit_hash=commit_hash,
            project_name=project_name,
            timeout_seconds=timeout_seconds or self.default_timeout,
            metadata=metadata or {},
        )

        self.sessions[session_id] = session
        logger.info(f"Created session {session_id} for commit {commit_hash}")

        return session

    async def get_session(self, session_id: UUID) -> Session | None:
        """
        Get a session by ID.

        Args:
            session_id: UUID of the session

        Returns:
            Session if found, None otherwise
        """
        session = self.sessions.get(session_id)

        if session and session.is_timed_out():
            await self._timeout_session(session)
            return None

        return session

    async def update_session_state(
        self,
        session_id: UUID,
        new_state: SessionState,
        metadata_updates: dict[str, Any] | None = None,
    ) -> bool:
        """
        Update the state of a session.

        Args:
            session_id: UUID of the session
            new_state: New state to set
            metadata_updates: Optional metadata updates

        Returns:
            True if updated, False if session not found
        """
        session = await self.get_session(session_id)
        if not session:
            return False

        session.state = new_state
        session.update_activity()

        if metadata_updates:
            session.metadata.update(metadata_updates)

        logger.debug(f"Updated session {session_id} state to {new_state}")
        return True

    async def complete_session(self, session_id: UUID) -> bool:
        """
        Mark a session as completed.

        Args:
            session_id: UUID of the session

        Returns:
            True if completed, False if session not found
        """
        return await self.update_session_state(session_id, SessionState.COMPLETED)

    async def cancel_session(self, session_id: UUID) -> bool:
        """
        Cancel a session.

        Args:
            session_id: UUID of the session

        Returns:
            True if cancelled, False if session not found
        """
        session = await self.get_session(session_id)
        if not session:
            return False

        # Terminate CLI process if running
        if session.cli_process:
            try:
                session.cli_process.terminate()
                await asyncio.wait_for(session.cli_process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                session.cli_process.kill()
                await session.cli_process.wait()
            except Exception as e:
                logger.error(f"Error terminating CLI process: {e}")

        await self.update_session_state(session_id, SessionState.CANCELLED)
        logger.info(f"Cancelled session {session_id}")
        return True

    async def list_active_sessions(self) -> list[Session]:
        """
        Get list of all active sessions.

        Returns:
            List of active Session objects
        """
        active_sessions = []
        for session in self.sessions.values():
            if session.is_timed_out():
                await self._timeout_session(session)
            elif session.is_active():
                active_sessions.append(session)

        return active_sessions

    async def get_session_count(self) -> dict[str, int]:
        """
        Get count of sessions by state.

        Returns:
            Dictionary mapping state names to counts
        """
        counts = {state.value: 0 for state in SessionState}

        for session in self.sessions.values():
            if session.is_timed_out():
                counts[SessionState.TIMED_OUT.value] += 1
            else:
                counts[session.state.value] += 1

        counts["total"] = len(self.sessions)
        counts["active"] = (
            counts[SessionState.INITIALIZING.value] + counts[SessionState.ACTIVE.value]
        )

        return counts

    async def _cleanup_loop(self):
        """Background task to periodically cleanup stale sessions."""
        logger.info(f"Starting cleanup loop (interval: {self.cleanup_interval}s)")

        while self._running:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_stale_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")

    async def _cleanup_stale_sessions(self):
        """Clean up timed out and old completed sessions."""
        now = datetime.now()
        stale_threshold = timedelta(hours=1)  # Keep completed sessions for 1 hour

        sessions_to_remove = []

        for session_id, session in self.sessions.items():
            # Timeout active sessions that have expired
            if session.is_active() and session.is_timed_out():
                await self._timeout_session(session)

            # Remove old completed/cancelled sessions
            if session.state in (
                SessionState.COMPLETED,
                SessionState.CANCELLED,
                SessionState.TIMED_OUT,
            ):
                age = now - session.last_activity
                if age > stale_threshold:
                    sessions_to_remove.append(session_id)

        # Remove stale sessions
        for session_id in sessions_to_remove:
            del self.sessions[session_id]
            logger.debug(f"Removed stale session {session_id}")

        if sessions_to_remove:
            logger.info(f"Cleaned up {len(sessions_to_remove)} stale sessions")

    async def _timeout_session(self, session: Session):
        """Handle a session timeout."""
        # Terminate CLI process if running
        if session.cli_process:
            try:
                session.cli_process.terminate()
                await asyncio.wait_for(session.cli_process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                session.cli_process.kill()
                await session.cli_process.wait()
            except Exception as e:
                logger.error(f"Error terminating timed out CLI process: {e}")

        session.state = SessionState.TIMED_OUT
        logger.warning(f"Session {session.session_id} timed out")

    async def _cleanup_all_sessions(self):
        """Clean up all sessions (called on shutdown)."""
        for session in self.sessions.values():
            if session.cli_process and session.is_active():
                try:
                    session.cli_process.terminate()
                    await asyncio.wait_for(session.cli_process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    session.cli_process.kill()
                    await session.cli_process.wait()
                except Exception as e:
                    logger.error(f"Error cleaning up session {session.session_id}: {e}")

        self.sessions.clear()
        logger.info("All sessions cleaned up")
