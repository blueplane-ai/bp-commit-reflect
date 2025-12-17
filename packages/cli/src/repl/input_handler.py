"""Async input handler for non-blocking stdin reading."""

import asyncio
import sys


class AsyncInputHandler:
    """Non-blocking stdin input handler using asyncio.

    Allows reading user input while simultaneously handling other async
    events (like HTTP requests from the commit notification server).
    """

    def __init__(self):
        """Initialize the input handler."""
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._running = False
        self._loop: asyncio.AbstractEventLoop | None = None

    async def start(self) -> None:
        """Start listening for stdin input.

        Registers a reader callback with the event loop for non-blocking
        stdin reading (Unix-like systems).
        """
        self._running = True
        self._loop = asyncio.get_event_loop()

        # Add stdin reader (works on Unix-like systems)
        # On Windows, this may need a different approach
        try:
            self._loop.add_reader(sys.stdin.fileno(), self._stdin_callback)
        except (ValueError, OSError):
            # stdin might not be readable (e.g., piped input exhausted)
            pass

    async def stop(self) -> None:
        """Stop listening for stdin input."""
        self._running = False
        if self._loop:
            try:
                self._loop.remove_reader(sys.stdin.fileno())
            except (ValueError, OSError):
                pass

    def _stdin_callback(self) -> None:
        """Called when stdin has data available.

        Reads a line and puts it in the queue for async consumption.
        """
        if not self._running:
            return

        try:
            line = sys.stdin.readline()
            if line:
                # Put in queue without blocking
                try:
                    self._queue.put_nowait(line.rstrip("\n\r"))
                except asyncio.QueueFull:
                    pass
        except (EOFError, OSError):
            # stdin closed or error
            pass

    async def get_input(self, timeout: float | None = None) -> str | None:
        """Get the next line of input.

        Args:
            timeout: Maximum seconds to wait (None = wait forever)

        Returns:
            Input line (stripped) or None if timeout/no input
        """
        try:
            if timeout is not None:
                return await asyncio.wait_for(self._queue.get(), timeout=timeout)
            return await self._queue.get()
        except asyncio.TimeoutError:
            return None
        except asyncio.CancelledError:
            return None

    async def prompt(
        self,
        message: str,
        timeout: float | None = None,
    ) -> str | None:
        """Display a prompt and wait for input.

        Args:
            message: Prompt message to display
            timeout: Maximum seconds to wait (None = wait forever)

        Returns:
            User input (stripped) or None if timeout
        """
        print(message, end="", flush=True)
        return await self.get_input(timeout)

    async def prompt_yes_no(
        self,
        message: str,
        default: bool | None = None,
        timeout: float | None = None,
    ) -> bool | None:
        """Prompt for yes/no response.

        Args:
            message: Prompt message (should include y/n hint)
            default: Default value if empty input
            timeout: Maximum seconds to wait

        Returns:
            True for yes, False for no, None if timeout/cancelled
        """
        response = await self.prompt(message, timeout)

        if response is None:
            return None

        response = response.strip().lower()

        if response in ("y", "yes"):
            return True
        elif response in ("n", "no"):
            return False
        elif response == "" and default is not None:
            return default
        else:
            return None  # Invalid response

    def clear_queue(self) -> int:
        """Clear any pending input from the queue.

        Returns:
            Number of items cleared
        """
        count = 0
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                count += 1
            except asyncio.QueueEmpty:
                break
        return count

    @property
    def is_running(self) -> bool:
        """Check if input handler is active."""
        return self._running

    def __repr__(self) -> str:
        status = "running" if self._running else "stopped"
        pending = self._queue.qsize()
        return f"AsyncInputHandler({status}, pending={pending})"
