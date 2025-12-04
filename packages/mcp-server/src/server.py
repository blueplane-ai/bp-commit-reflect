"""
MCP Server core implementation for Commit Reflection System.

This module implements the main MCP server that coordinates CLI processes
and provides MCP tools for AI agents to interact with the reflection system.
"""

import asyncio
import json
import logging
import signal
from pathlib import Path
from typing import Dict, Any, Optional, List
from uuid import UUID

from .session_manager import SessionManager, SessionState


logger = logging.getLogger(__name__)


class MCPReflectionServer:
    """
    Main MCP server for commit reflection system.

    Coordinates CLI processes and provides MCP tools for:
    - Starting reflection sessions
    - Answering questions
    - Completing reflections
    - Cancelling sessions
    - Querying recent reflections
    """

    def __init__(
        self,
        max_concurrent_sessions: int = 10,
        session_timeout: int = 1800,
        cleanup_interval: int = 300,
        cli_command: str = "commit-reflect",
    ):
        """
        Initialize the MCP server.

        Args:
            max_concurrent_sessions: Maximum concurrent reflection sessions
            session_timeout: Session timeout in seconds
            cleanup_interval: Cleanup interval in seconds
            cli_command: Command to execute for CLI processes
        """
        self.session_manager = SessionManager(
            max_concurrent_sessions=max_concurrent_sessions,
            default_timeout=session_timeout,
            cleanup_interval=cleanup_interval,
        )
        self.cli_command = cli_command
        self._running = False
        self._shutdown_event = asyncio.Event()

    async def start(self):
        """Start the MCP server."""
        if self._running:
            logger.warning("Server already running")
            return

        logger.info("Starting MCP Reflection Server")
        self._running = True

        # Start session manager
        await self.session_manager.start()

        # Setup signal handlers for graceful shutdown
        self._setup_signal_handlers()

        logger.info("MCP Reflection Server started successfully")

    async def stop(self):
        """Stop the MCP server gracefully."""
        if not self._running:
            return

        logger.info("Stopping MCP Reflection Server")
        self._running = False

        # Stop session manager
        await self.session_manager.stop()

        # Signal shutdown complete
        self._shutdown_event.set()

        logger.info("MCP Reflection Server stopped")

    async def wait_for_shutdown(self):
        """Wait for shutdown signal."""
        await self._shutdown_event.wait()

    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        loop = asyncio.get_event_loop()

        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(
                sig,
                lambda s=sig: asyncio.create_task(self._handle_shutdown_signal(s))
            )

    async def _handle_shutdown_signal(self, sig):
        """Handle shutdown signals."""
        logger.info(f"Received shutdown signal: {sig.name}")
        await self.stop()

    # MCP Tool Implementations

    async def start_reflection(
        self,
        commit_hash: str,
        project_name: Optional[str] = None,
        branch: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        MCP Tool: Start a new commit reflection session.

        Args:
            commit_hash: The commit hash to reflect on
            project_name: Optional project name
            branch: Optional branch name
            **kwargs: Additional metadata

        Returns:
            Dictionary with session_id and first question
        """
        try:
            # Create session
            session = await self.session_manager.create_session(
                commit_hash=commit_hash,
                project_name=project_name,
                metadata={"branch": branch, **kwargs}
            )

            # Spawn CLI process
            cli_process = await self._spawn_cli_process(
                commit_hash=commit_hash,
                project_name=project_name,
                branch=branch,
            )

            session.cli_process = cli_process
            await self.session_manager.update_session_state(
                session.session_id,
                SessionState.ACTIVE
            )

            # Get first question from CLI
            first_question = await self._get_next_question(session)

            return {
                "success": True,
                "session_id": str(session.session_id),
                "question": first_question,
                "message": "Reflection session started"
            }

        except Exception as e:
            logger.error(f"Error starting reflection: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to start reflection session"
            }

    async def answer_question(
        self,
        session_id: str,
        answer: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        MCP Tool: Answer a reflection question.

        Args:
            session_id: The session ID
            answer: The answer to the current question
            **kwargs: Additional metadata

        Returns:
            Dictionary with next question or completion status
        """
        try:
            session_uuid = UUID(session_id)
            session = await self.session_manager.get_session(session_uuid)

            if not session:
                return {
                    "success": False,
                    "error": "Session not found or expired",
                    "message": "Invalid session"
                }

            if not session.is_active():
                return {
                    "success": False,
                    "error": f"Session is in {session.state} state",
                    "message": "Session not active"
                }

            # Send answer to CLI process
            await self._send_answer_to_cli(session, answer)

            # Update session activity
            session.update_activity()
            session.current_question_index += 1

            # Get next question
            next_question = await self._get_next_question(session)

            if next_question is None:
                # No more questions - session complete
                await self.session_manager.complete_session(session_uuid)
                return {
                    "success": True,
                    "completed": True,
                    "message": "Reflection completed successfully"
                }

            return {
                "success": True,
                "completed": False,
                "question": next_question,
                "question_index": session.current_question_index,
                "message": "Answer recorded"
            }

        except Exception as e:
            logger.error(f"Error answering question: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to record answer"
            }

    async def complete_reflection(
        self,
        session_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        MCP Tool: Complete a reflection session.

        Args:
            session_id: The session ID
            **kwargs: Additional metadata

        Returns:
            Dictionary with completion status
        """
        try:
            session_uuid = UUID(session_id)
            session = await self.session_manager.get_session(session_uuid)

            if not session:
                return {
                    "success": False,
                    "error": "Session not found or expired",
                    "message": "Invalid session"
                }

            # Send completion signal to CLI
            if session.cli_process:
                await self._complete_cli_session(session)

            # Mark session as completed
            await self.session_manager.complete_session(session_uuid)

            return {
                "success": True,
                "message": "Reflection completed and saved"
            }

        except Exception as e:
            logger.error(f"Error completing reflection: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to complete reflection"
            }

    async def cancel_reflection(
        self,
        session_id: str,
        reason: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        MCP Tool: Cancel a reflection session.

        Args:
            session_id: The session ID
            reason: Optional cancellation reason
            **kwargs: Additional metadata

        Returns:
            Dictionary with cancellation status
        """
        try:
            session_uuid = UUID(session_id)
            success = await self.session_manager.cancel_session(session_uuid)

            if not success:
                return {
                    "success": False,
                    "error": "Session not found or already ended",
                    "message": "Invalid session"
                }

            return {
                "success": True,
                "message": f"Reflection cancelled{': ' + reason if reason else ''}"
            }

        except Exception as e:
            logger.error(f"Error cancelling reflection: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to cancel reflection"
            }

    async def get_recent_reflections(
        self,
        limit: int = 10,
        project_name: Optional[str] = None,
        since: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        MCP Tool: Get recent reflections.

        Args:
            limit: Maximum number of reflections to return
            project_name: Optional project name filter
            since: Optional ISO timestamp to filter reflections since
            **kwargs: Additional filters

        Returns:
            Dictionary with list of recent reflections
        """
        try:
            # Import storage utilities
            from shared.storage.factory import create_storage_from_config
            from shared.types.config import StorageConfig, Config
            from shared.types.storage import QueryOptions
            from datetime import datetime, timezone

            # Load default configuration or try common paths
            config = Config()

            # Try to load config from common locations
            config_paths = [
                Path('.commit-reflect') / 'config.json',
                Path.home() / '.commit-reflect' / 'config.json',
            ]

            for config_path in config_paths:
                if config_path.exists():
                    try:
                        import json
                        with open(config_path, 'r') as f:
                            config_data = json.load(f)
                            if 'storage' in config_data:
                                config.storage = [
                                    StorageConfig(**s) if isinstance(s, dict) else s
                                    for s in config_data['storage']
                                ]
                            break
                    except Exception as e:
                        logger.warning(f"Failed to load config from {config_path}: {e}")

            # If no config found, use defaults
            if not config.storage:
                config.storage = [
                    StorageConfig(
                        backend='jsonl',
                        path='.commit-reflections.jsonl',
                        enabled=True,
                    )
                ]

            # Try each enabled storage backend
            all_reflections = []
            errors = []

            for storage_config in config.storage:
                if not storage_config.enabled:
                    continue

                try:
                    storage = create_storage_from_config(storage_config)

                    # Build query options
                    query_opts = QueryOptions(limit=limit * 2)  # Get extra in case we filter

                    # Query storage
                    reflections = storage.read_recent(**query_opts.to_dict())
                    storage.close()

                    # Apply filters
                    for reflection in reflections:
                        # Project filter
                        if project_name and reflection.get('project') != project_name:
                            continue

                        # Time filter
                        if since:
                            try:
                                since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
                                reflection_dt = datetime.fromisoformat(
                                    reflection.get('timestamp', '').replace('Z', '+00:00')
                                )
                                if reflection_dt < since_dt:
                                    continue
                            except (ValueError, AttributeError):
                                pass

                        all_reflections.append(reflection)

                    # We got results from this backend, that's enough
                    if all_reflections:
                        break

                except Exception as e:
                    logger.warning(f"Failed to query {storage_config.backend}: {e}")
                    errors.append(f"{storage_config.backend}: {str(e)}")

            # Sort by timestamp (most recent first) and limit
            all_reflections.sort(
                key=lambda r: r.get('timestamp', ''),
                reverse=True
            )
            all_reflections = all_reflections[:limit]

            result = {
                "success": True,
                "reflections": all_reflections,
                "count": len(all_reflections),
                "message": f"Found {len(all_reflections)} reflection(s)"
            }

            if errors:
                result["warnings"] = errors

            return result

        except Exception as e:
            logger.error(f"Error getting recent reflections: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to query reflections"
            }

    async def get_session_status(
        self,
        session_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get status of a reflection session.

        Args:
            session_id: The session ID
            **kwargs: Additional parameters

        Returns:
            Dictionary with session status
        """
        try:
            session_uuid = UUID(session_id)
            session = await self.session_manager.get_session(session_uuid)

            if not session:
                return {
                    "success": False,
                    "error": "Session not found",
                    "message": "Invalid session"
                }

            return {
                "success": True,
                "session": session.to_dict(),
                "message": "Session found"
            }

        except Exception as e:
            logger.error(f"Error getting session status: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to get session status"
            }

    async def get_server_stats(self) -> Dict[str, Any]:
        """
        Get server statistics.

        Returns:
            Dictionary with server stats
        """
        try:
            session_counts = await self.session_manager.get_session_count()

            return {
                "success": True,
                "stats": {
                    "running": self._running,
                    "sessions": session_counts,
                    "max_concurrent": self.session_manager.max_concurrent_sessions,
                },
                "message": "Server stats retrieved"
            }

        except Exception as e:
            logger.error(f"Error getting server stats: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to get server stats"
            }

    # CLI Process Management

    async def _spawn_cli_process(
        self,
        commit_hash: str,
        project_name: Optional[str] = None,
        branch: Optional[str] = None,
    ) -> asyncio.subprocess.Process:
        """
        Spawn a CLI process for reflection.

        Args:
            commit_hash: Commit hash to reflect on
            project_name: Optional project name
            branch: Optional branch name

        Returns:
            Subprocess.Process object
        """
        # Build CLI command
        cmd = [self.cli_command, "--mode", "mcp-session"]

        if commit_hash:
            cmd.extend(["--commit", commit_hash])
        if project_name:
            cmd.extend(["--project", project_name])
        if branch:
            cmd.extend(["--branch", branch])

        # Spawn process
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        logger.debug(f"Spawned CLI process: {' '.join(cmd)}")
        return process

    async def _send_answer_to_cli(self, session, answer: str):
        """
        Send an answer to the CLI process.

        Args:
            session: Session object
            answer: Answer text
        """
        if not session.cli_process or not session.cli_process.stdin:
            raise RuntimeError("CLI process not available")

        # Send answer as JSON
        message = json.dumps({"answer": answer}) + "\n"
        session.cli_process.stdin.write(message.encode())
        await session.cli_process.stdin.drain()

    async def _get_next_question(self, session) -> Optional[Dict[str, Any]]:
        """
        Get the next question from CLI process.

        Args:
            session: Session object

        Returns:
            Question dictionary or None if no more questions
        """
        if not session.cli_process or not session.cli_process.stdout:
            raise RuntimeError("CLI process not available")

        try:
            # Read next line from CLI stdout
            line = await asyncio.wait_for(
                session.cli_process.stdout.readline(),
                timeout=5.0
            )

            if not line:
                return None

            # Parse JSON response
            data = json.loads(line.decode())
            return data.get("question")

        except asyncio.TimeoutError:
            logger.error("Timeout waiting for question from CLI")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse CLI response: {e}")
            return None

    async def _complete_cli_session(self, session):
        """
        Send completion signal to CLI process.

        Args:
            session: Session object
        """
        if not session.cli_process or not session.cli_process.stdin:
            return

        try:
            # Send completion signal
            message = json.dumps({"action": "complete"}) + "\n"
            session.cli_process.stdin.write(message.encode())
            await session.cli_process.stdin.drain()

            # Wait for process to complete
            await asyncio.wait_for(session.cli_process.wait(), timeout=10.0)

        except asyncio.TimeoutError:
            logger.warning("Timeout waiting for CLI to complete, terminating")
            session.cli_process.terminate()
            await session.cli_process.wait()
        except Exception as e:
            logger.error(f"Error completing CLI session: {e}")
