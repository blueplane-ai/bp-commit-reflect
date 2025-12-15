"""HTTP server for receiving commit notifications from git hooks."""

import asyncio
import json
import urllib.parse
from datetime import datetime
from typing import Optional, Callable

from .queue import QueuedCommit


class CommitNotificationServer:
    """Minimal asyncio HTTP server for receiving commit notifications.

    Listens for POST requests to /commit endpoint with commit data.
    Designed to be lightweight and fail gracefully.
    """

    def __init__(
        self,
        port: int = 9123,
        host: str = "127.0.0.1",
        on_commit: Optional[Callable[[QueuedCommit], None]] = None,
    ):
        """Initialize the server.

        Args:
            port: Port to listen on (default: 9123)
            host: Host to bind to (default: localhost only)
            on_commit: Callback when commit notification received
        """
        self.port = port
        self.host = host
        self.on_commit = on_commit
        self._server: Optional[asyncio.Server] = None
        self._running = False

    async def start(self) -> None:
        """Start the HTTP server.

        Raises:
            OSError: If port is already in use
        """
        self._server = await asyncio.start_server(
            self._handle_connection,
            self.host,
            self.port,
        )
        self._running = True

    async def stop(self) -> None:
        """Stop the HTTP server gracefully."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        self._running = False

    @property
    def is_running(self) -> bool:
        """Check if server is currently running."""
        return self._running

    async def _handle_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handle an incoming HTTP connection.

        Args:
            reader: Stream reader for request data
            writer: Stream writer for response
        """
        try:
            # Read the HTTP request (limit to 8KB for safety)
            data = await asyncio.wait_for(reader.read(8192), timeout=5.0)
            request = data.decode("utf-8", errors="replace")

            # Parse and handle the request
            response = self._handle_request(request)

            # Send response
            writer.write(response.encode("utf-8"))
            await writer.drain()

        except asyncio.TimeoutError:
            # Client took too long, just close
            pass
        except Exception:
            # Log error but don't crash server
            pass
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    def _handle_request(self, request: str) -> str:
        """Parse HTTP request and generate response.

        Args:
            request: Raw HTTP request string

        Returns:
            HTTP response string
        """
        # Parse request line
        lines = request.split("\r\n")
        if not lines:
            return self._response(400, "Bad Request")

        request_line = lines[0]
        parts = request_line.split(" ")
        if len(parts) < 2:
            return self._response(400, "Bad Request")

        method, path = parts[0], parts[1]

        # Only handle POST /commit
        if method == "POST" and path == "/commit":
            commit = self._parse_commit_request(request)
            if commit:
                # Call the callback (non-blocking)
                if self.on_commit:
                    try:
                        self.on_commit(commit)
                    except Exception:
                        pass
                return self._response(200, "OK")
            else:
                return self._response(400, "Invalid commit data")

        # Health check endpoint
        elif method == "GET" and path == "/health":
            return self._response(200, "OK")

        else:
            return self._response(404, "Not Found")

    def _parse_commit_request(self, request: str) -> Optional[QueuedCommit]:
        """Parse commit data from HTTP request body.

        Supports both URL-encoded and JSON formats.

        Args:
            request: Raw HTTP request string

        Returns:
            QueuedCommit if parsing successful, None otherwise
        """
        try:
            # Find body (after double CRLF)
            body_start = request.find("\r\n\r\n")
            if body_start == -1:
                return None

            body = request[body_start + 4 :].strip()
            if not body:
                return None

            # Try JSON first
            if body.startswith("{"):
                data = json.loads(body)
            else:
                # URL-encoded: hash=abc&project=foo&branch=main
                data = dict(urllib.parse.parse_qsl(body))

            # Extract fields (support both naming conventions)
            commit_hash = data.get("hash") or data.get("commit_hash", "")
            project = data.get("project", "unknown")
            branch = data.get("branch", "unknown")
            repo_path = data.get("repo_path")  # Path to git repository

            if not commit_hash:
                return None

            return QueuedCommit(
                commit_hash=commit_hash,
                project=project,
                branch=branch,
                repo_path=repo_path,
                received_at=datetime.now(),
            )

        except (json.JSONDecodeError, ValueError):
            return None

    def _response(self, status_code: int, status_text: str, body: str = "") -> str:
        """Generate an HTTP response.

        Args:
            status_code: HTTP status code
            status_text: HTTP status text
            body: Optional response body

        Returns:
            Complete HTTP response string
        """
        if not body:
            body = status_text

        return (
            f"HTTP/1.1 {status_code} {status_text}\r\n"
            f"Content-Type: text/plain\r\n"
            f"Content-Length: {len(body)}\r\n"
            f"Connection: close\r\n"
            f"\r\n"
            f"{body}"
        )

    def __repr__(self) -> str:
        status = "running" if self._running else "stopped"
        return f"CommitNotificationServer({self.host}:{self.port}, {status})"
