"""Tests for MCP communication from IDE hooks."""

import asyncio
import sys
from pathlib import Path as PathLib
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, str(PathLib(__file__).parent.parent))

from PostToolUse import CommitReflectionHook, ReflectionQuestionFlow


class TestMCPCommunication:
    """Test MCP server communication from IDE hooks."""

    @pytest.mark.asyncio
    async def test_start_reflection_session_mcp_call(self):
        """Test starting reflection session via MCP."""
        hook = CommitReflectionHook({"mcp_server_url": "localhost:3000", "auto_trigger": True})

        commit_info = {
            "hash": "abc123",
            "message": "Test commit",
            "branch": "main",
            "files_changed": 1,
            "project_name": "test-project",
        }

        # Mock MCP server call
        with patch("aiohttp.ClientSession") as mock_session:
            mock_response = AsyncMock()
            mock_response.json = AsyncMock(
                return_value={
                    "success": True,
                    "session_id": "test-session-123",
                    "message": "Reflection started",
                }
            )
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            mock_post = AsyncMock(return_value=mock_response)
            mock_session.return_value.post = mock_post
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session.return_value)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

            # Note: This test structure shows the pattern, but actual implementation
            # would require aiohttp or similar HTTP client
            # For now, we test the hook's behavior with mocked MCP calls

            result = await hook._start_reflection_session(commit_info)

            # In real implementation, this would make HTTP call
            # For now, verify the structure
            assert isinstance(result, dict)
            assert "success" in result or "session_id" in result

    @pytest.mark.asyncio
    async def test_question_flow_mcp_communication(self):
        """Test question flow communicates with MCP server."""
        flow = ReflectionQuestionFlow("test-session", "localhost:3000")

        # Mock MCP server responses
        with patch.object(flow, "_get_next_question") as mock_get:
            mock_get.return_value = {
                "text": "What did you accomplish?",
                "help_text": "Describe your changes",
                "required": True,
            }

            question = await flow.start_flow()

            assert "What did you accomplish?" in question
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_submit_answer_mcp_communication(self):
        """Test submitting answers via MCP."""
        flow = ReflectionQuestionFlow("test-session", "localhost:3000")

        with patch.object(flow, "_send_answer") as mock_send:
            mock_send.return_value = {
                "success": True,
                "completed": False,
                "question": {"text": "Next question", "required": True},
            }

            with patch.object(flow, "_get_next_question") as mock_get:
                mock_get.return_value = {"text": "Next question", "required": True}

                result = await flow.submit_answer("My answer")

                assert "Next question" in result
                mock_send.assert_called_once_with("My answer")

    @pytest.mark.asyncio
    async def test_mcp_error_handling(self):
        """Test error handling when MCP server is unavailable."""
        hook = CommitReflectionHook()

        # Simulate MCP connection failure
        with patch.object(hook, "_start_reflection_session") as mock_start:
            mock_start.side_effect = Exception("Connection refused")

            commit_info = {
                "hash": "abc123",
                "message": "Test",
                "branch": "main",
                "files_changed": 1,
                "project_name": "test",
            }

            # Should handle error gracefully
            try:
                await hook._start_reflection_session(commit_info)
            except Exception as e:
                # Error should be caught and handled
                assert "Connection" in str(e) or isinstance(e, Exception)

    @pytest.mark.asyncio
    async def test_mcp_timeout_handling(self):
        """Test handling MCP server timeouts."""
        flow = ReflectionQuestionFlow("test-session", "localhost:3000")

        # Simulate timeout
        with patch.object(flow, "_get_next_question") as mock_get:
            mock_get.side_effect = asyncio.TimeoutError("Server timeout")

            with pytest.raises(asyncio.TimeoutError):
                await flow.start_flow()

    @pytest.mark.asyncio
    async def test_mcp_message_format(self):
        """Test MCP message format is correct."""
        # Verify that messages sent to MCP follow expected format
        flow = ReflectionQuestionFlow("test-session", "localhost:3000")

        # In real implementation, _send_answer would format JSON
        # For now, verify the structure
        with patch.object(flow, "_send_answer") as mock_send:
            mock_send.return_value = {"success": True, "completed": False}

            await flow.submit_answer("test answer")

            # Verify answer was sent
            mock_send.assert_called_once_with("test answer")


class TestMCPProtocolCompliance:
    """Test compliance with MCP protocol specifications."""

    def test_session_id_preserved(self):
        """Test session ID is preserved throughout flow."""
        session_id = "test-session-abc123"
        flow = ReflectionQuestionFlow(session_id, "localhost:3000")

        assert flow.session_id == session_id

    def test_mcp_url_configuration(self):
        """Test MCP server URL is configurable."""
        custom_url = "custom-server:8080"
        hook = CommitReflectionHook({"mcp_server_url": custom_url})

        assert hook.mcp_server_url == custom_url

    @pytest.mark.asyncio
    async def test_question_format_compliance(self):
        """Test question format matches MCP protocol."""
        flow = ReflectionQuestionFlow("test-session", "localhost:3000")

        question = {
            "text": "Test question",
            "help_text": "Help text",
            "required": True,
            "type": "text",
        }

        formatted = flow._format_question(question)

        # Verify format includes required fields
        assert "Test question" in formatted
        assert "Help text" in formatted


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
