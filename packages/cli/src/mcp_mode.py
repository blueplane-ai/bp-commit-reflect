"""MCP (Model Context Protocol) mode for CLI.

This module implements the MCP session mode where the CLI communicates
via JSON messages over stdin/stdout with an MCP server.
"""

import json
import sys
from datetime import datetime
from enum import Enum
from typing import Any


class MessageType(Enum):
    """MCP message types."""

    REQUEST = "request"
    RESPONSE = "response"
    ERROR = "error"
    STATE = "state"


class MCPCommunicator:
    """
    Handles JSON-based communication for MCP mode.

    Reads JSON messages from stdin and writes responses to stdout.
    """

    def __init__(self):
        """Initialize MCP communicator."""
        self.session_id: str | None = None

    def read_message(self) -> dict[str, Any] | None:
        """
        Read a JSON message from stdin.

        Returns:
            Message dictionary, or None if stdin is closed
        """
        try:
            line = sys.stdin.readline()
            if not line:
                return None

            message = json.loads(line.strip())
            return message

        except json.JSONDecodeError as e:
            self.send_error(f"Invalid JSON: {e}")
            return None
        except Exception as e:
            self.send_error(f"Error reading message: {e}")
            return None

    def send_response(
        self, data: dict[str, Any], message_type: MessageType = MessageType.RESPONSE
    ) -> None:
        """
        Send a JSON response to stdout.

        Args:
            data: Response data dictionary
            message_type: Type of message
        """
        message = {
            "type": message_type.value,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "data": data,
        }

        if self.session_id:
            message["session_id"] = self.session_id

        try:
            json.dump(message, sys.stdout)
            sys.stdout.write("\n")
            sys.stdout.flush()
        except Exception as e:
            # Can't send error via stdout if stdout failed
            sys.stderr.write(f"Error sending response: {e}\n")

    def send_error(self, error_message: str, error_code: str | None = None) -> None:
        """
        Send an error response.

        Args:
            error_message: Human-readable error message
            error_code: Optional error code
        """
        error_data = {"error": error_message}

        if error_code:
            error_data["code"] = error_code

        self.send_response(error_data, MessageType.ERROR)

    def send_state(self, state: dict[str, Any]) -> None:
        """
        Send session state update.

        Args:
            state: Session state dictionary
        """
        self.send_response(state, MessageType.STATE)


class SessionStateSerializer:
    """
    Serializes and deserializes session state for MCP communication.
    """

    @staticmethod
    def serialize(session_state: dict[str, Any]) -> dict[str, Any]:
        """
        Serialize session state to JSON-compatible format.

        Args:
            session_state: Session state dictionary

        Returns:
            Serialized state dictionary
        """
        serialized = {
            "session_id": session_state.get("session_id"),
            "project": session_state.get("project"),
            "branch": session_state.get("branch"),
            "commit_hash": session_state.get("commit_hash"),
            "commit_message": session_state.get("commit_message"),
            "current_question_index": session_state.get("current_question_index", 0),
            "answers": session_state.get("answers", {}),
            "started_at": session_state.get("started_at"),
            "last_activity": datetime.utcnow().isoformat() + "Z",
            "status": session_state.get("status", "active"),
        }

        return {k: v for k, v in serialized.items() if v is not None}

    @staticmethod
    def deserialize(data: dict[str, Any]) -> dict[str, Any]:
        """
        Deserialize session state from JSON format.

        Args:
            data: Serialized state dictionary

        Returns:
            Session state dictionary
        """
        return {
            "session_id": data.get("session_id"),
            "project": data.get("project"),
            "branch": data.get("branch"),
            "commit_hash": data.get("commit_hash"),
            "commit_message": data.get("commit_message"),
            "current_question_index": data.get("current_question_index", 0),
            "answers": data.get("answers", {}),
            "started_at": data.get("started_at"),
            "last_activity": data.get("last_activity"),
            "status": data.get("status", "active"),
        }


class MCPSessionHandler:
    """
    Handles MCP session lifecycle and command processing.
    """

    def __init__(self, communicator: MCPCommunicator):
        """
        Initialize MCP session handler.

        Args:
            communicator: MCPCommunicator instance
        """
        self.comm = communicator
        self.state = {}

    def handle_command(self, message: dict[str, Any]) -> bool:
        """
        Handle an MCP command message.

        Args:
            message: Command message dictionary

        Returns:
            True to continue processing, False to exit
        """
        command = message.get("command")

        if not command:
            self.comm.send_error("Missing 'command' field")
            return True

        # Dispatch to command handlers
        handlers = {
            "init": self._handle_init,
            "answer": self._handle_answer,
            "get_state": self._handle_get_state,
            "complete": self._handle_complete,
            "cancel": self._handle_cancel,
        }

        handler = handlers.get(command)
        if not handler:
            self.comm.send_error(f"Unknown command: {command}", error_code="UNKNOWN_COMMAND")
            return True

        try:
            return handler(message)
        except Exception as e:
            self.comm.send_error(str(e), error_code="COMMAND_FAILED")
            return True

    def _handle_init(self, message: dict[str, Any]) -> bool:
        """Handle session initialization."""
        data = message.get("data", {})

        # Initialize session state
        self.state = {
            "session_id": data.get("session_id"),
            "project": data.get("project"),
            "branch": data.get("branch"),
            "commit_hash": data.get("commit_hash"),
            "commit_message": data.get("commit_message"),
            "current_question_index": 0,
            "answers": {},
            "started_at": datetime.utcnow().isoformat() + "Z",
            "status": "active",
        }

        self.comm.session_id = self.state["session_id"]

        # Send initial state
        self.comm.send_state(SessionStateSerializer.serialize(self.state))

        return True

    def _handle_answer(self, message: dict[str, Any]) -> bool:
        """Handle answer submission."""
        data = message.get("data", {})

        question_id = data.get("question_id")
        answer = data.get("answer")

        if not question_id:
            self.comm.send_error("Missing 'question_id' field")
            return True

        # Store answer
        self.state["answers"][question_id] = answer
        self.state["current_question_index"] += 1

        # Send updated state
        self.comm.send_state(SessionStateSerializer.serialize(self.state))

        return True

    def _handle_get_state(self, message: dict[str, Any]) -> bool:
        """Handle state query."""
        self.comm.send_state(SessionStateSerializer.serialize(self.state))
        return True

    def _handle_complete(self, message: dict[str, Any]) -> bool:
        """Handle session completion."""
        self.state["status"] = "completed"
        self.comm.send_response(
            {"status": "completed", "message": "Reflection session completed successfully"}
        )
        return False  # Exit after completion

    def _handle_cancel(self, message: dict[str, Any]) -> bool:
        """Handle session cancellation."""
        self.state["status"] = "cancelled"
        self.comm.send_response({"status": "cancelled", "message": "Reflection session cancelled"})
        return False  # Exit after cancellation


def run_mcp_mode() -> int:
    """
    Run CLI in MCP mode.

    Reads JSON messages from stdin and sends responses to stdout.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    communicator = MCPCommunicator()
    handler = MCPSessionHandler(communicator)

    try:
        # Send ready signal
        communicator.send_response({"status": "ready"})

        # Message processing loop
        while True:
            message = communicator.read_message()

            if message is None:
                # stdin closed, exit gracefully
                break

            # Handle command
            continue_processing = handler.handle_command(message)

            if not continue_processing:
                break

        return 0

    except KeyboardInterrupt:
        communicator.send_error("Interrupted by user", error_code="INTERRUPTED")
        return 1
    except Exception as e:
        communicator.send_error(f"Fatal error: {e}", error_code="FATAL_ERROR")
        return 1


if __name__ == "__main__":
    sys.exit(run_mcp_mode())
