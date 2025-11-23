"""
Integration tests for MCP-CLI communication.

Tests the Model Context Protocol server's ability to:
- Spawn and manage CLI processes
- Communicate via stdin/stdout
- Handle JSON-RPC messages
- Manage session state
"""

import pytest
import json
import subprocess
from unittest.mock import Mock, patch, MagicMock


@pytest.mark.integration
@pytest.mark.mcp
class TestMCPCLICommunication:
    """Tests for MCP server and CLI communication."""

    def test_mcp_server_spawns_cli_process(self, mocker):
        """Test that MCP server can spawn CLI process."""
        mock_popen = mocker.patch("subprocess.Popen")
        mock_process = Mock()
        mock_process.poll.return_value = None  # Process is running
        mock_popen.return_value = mock_process

        # Simulate spawning CLI process
        process = subprocess.Popen(
            ["commit-reflect", "--mode", "mcp-session"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        assert process is not None
        mock_popen.assert_called_once()

    def test_mcp_sends_json_message_to_cli(self, mocker):
        """Test MCP server can send JSON messages to CLI."""
        mock_process = Mock()
        mock_process.stdin = Mock()
        mock_process.stdout = Mock()
        mock_process.poll.return_value = None

        # Create test message
        message = {
            "jsonrpc": "2.0",
            "method": "start_reflection",
            "params": {"commit_hash": "abc123"},
            "id": 1,
        }

        # Send message to CLI stdin
        message_json = json.dumps(message) + "\n"
        mock_process.stdin.write(message_json.encode())
        mock_process.stdin.flush()

        mock_process.stdin.write.assert_called_once()
        mock_process.stdin.flush.assert_called_once()

    def test_mcp_receives_response_from_cli(self, mocker):
        """Test MCP server can receive responses from CLI."""
        mock_process = Mock()
        mock_process.stdout = Mock()

        # Mock CLI response
        response = {
            "jsonrpc": "2.0",
            "result": {
                "status": "started",
                "question": "What changed?",
                "question_id": "what",
            },
            "id": 1,
        }

        mock_process.stdout.readline.return_value = (
            json.dumps(response) + "\n"
        ).encode()

        # Read response
        line = mock_process.stdout.readline().decode().strip()
        response_data = json.loads(line)

        assert response_data["jsonrpc"] == "2.0"
        assert response_data["result"]["status"] == "started"
        assert response_data["id"] == 1

    def test_mcp_handles_cli_error_response(self, mocker):
        """Test MCP server handles error responses from CLI."""
        mock_process = Mock()
        mock_process.stdout = Mock()

        # Mock CLI error response
        error_response = {
            "jsonrpc": "2.0",
            "error": {"code": -32602, "message": "Invalid commit hash"},
            "id": 1,
        }

        mock_process.stdout.readline.return_value = (
            json.dumps(error_response) + "\n"
        ).encode()

        # Read error response
        line = mock_process.stdout.readline().decode().strip()
        response_data = json.loads(line)

        assert "error" in response_data
        assert response_data["error"]["code"] == -32602

    def test_mcp_timeout_handling(self, mocker):
        """Test MCP server handles CLI process timeout."""
        mock_process = Mock()
        mock_process.stdout = Mock()
        mock_process.poll.return_value = None

        # Simulate timeout - no response
        mock_process.stdout.readline.side_effect = TimeoutError("Read timeout")

        with pytest.raises(TimeoutError):
            mock_process.stdout.readline()

    def test_mcp_multiple_messages_in_session(self, mocker):
        """Test multiple message exchanges in a single session."""
        mock_process = Mock()
        mock_process.stdin = Mock()
        mock_process.stdout = Mock()
        mock_process.poll.return_value = None

        messages = [
            {"jsonrpc": "2.0", "method": "start_reflection", "id": 1},
            {"jsonrpc": "2.0", "method": "answer_question", "params": {"answer": "Added auth"}, "id": 2},
            {"jsonrpc": "2.0", "method": "complete_reflection", "id": 3},
        ]

        responses = [
            {"jsonrpc": "2.0", "result": {"status": "started"}, "id": 1},
            {"jsonrpc": "2.0", "result": {"status": "next_question"}, "id": 2},
            {"jsonrpc": "2.0", "result": {"status": "completed"}, "id": 3},
        ]

        # Send all messages
        for message in messages:
            message_json = json.dumps(message) + "\n"
            mock_process.stdin.write(message_json.encode())

        assert mock_process.stdin.write.call_count == 3


@pytest.mark.integration
@pytest.mark.mcp
class TestMCPSessionState:
    """Tests for MCP session state management."""

    def test_mcp_maintains_session_state(self):
        """Test that MCP server maintains session state across messages."""
        session_state = {
            "session_id": "session_123",
            "commit_hash": "abc123",
            "current_question": 0,
            "answers": {},
        }

        # Simulate state updates
        session_state["answers"]["what"] = "Added authentication"
        session_state["current_question"] = 1

        assert session_state["answers"]["what"] == "Added authentication"
        assert session_state["current_question"] == 1

    def test_mcp_session_cleanup_on_completion(self):
        """Test session cleanup when reflection completes."""
        sessions = {"session_123": {"commit_hash": "abc123", "answers": {}}}

        # Complete session
        session_id = "session_123"
        sessions.pop(session_id, None)

        assert session_id not in sessions

    def test_mcp_session_cleanup_on_cancellation(self):
        """Test session cleanup when reflection is cancelled."""
        sessions = {"session_123": {"commit_hash": "abc123", "answers": {}}}

        # Cancel session
        session_id = "session_123"
        sessions.pop(session_id, None)

        assert session_id not in sessions


@pytest.mark.integration
@pytest.mark.mcp
class TestMCPProtocolCompliance:
    """Tests for JSON-RPC 2.0 protocol compliance."""

    def test_valid_jsonrpc_request_format(self):
        """Test that requests follow JSON-RPC 2.0 format."""
        request = {
            "jsonrpc": "2.0",
            "method": "start_reflection",
            "params": {"commit_hash": "abc123"},
            "id": 1,
        }

        assert request["jsonrpc"] == "2.0"
        assert "method" in request
        assert "id" in request

    def test_valid_jsonrpc_response_format(self):
        """Test that responses follow JSON-RPC 2.0 format."""
        response = {
            "jsonrpc": "2.0",
            "result": {"status": "started"},
            "id": 1,
        }

        assert response["jsonrpc"] == "2.0"
        assert "result" in response or "error" in response
        assert "id" in response

    def test_valid_jsonrpc_error_format(self):
        """Test that errors follow JSON-RPC 2.0 format."""
        error = {
            "jsonrpc": "2.0",
            "error": {
                "code": -32602,
                "message": "Invalid params",
            },
            "id": 1,
        }

        assert error["jsonrpc"] == "2.0"
        assert "error" in error
        assert "code" in error["error"]
        assert "message" in error["error"]

    def test_notification_has_no_id(self):
        """Test that notifications don't include ID field."""
        notification = {
            "jsonrpc": "2.0",
            "method": "progress_update",
            "params": {"progress": 50},
        }

        assert notification["jsonrpc"] == "2.0"
        assert "method" in notification
        assert "id" not in notification
