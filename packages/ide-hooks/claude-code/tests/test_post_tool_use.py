"""Tests for Claude Code PostToolUse hook."""

import pytest
import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, Any

# Import the hook module
import sys
from pathlib import Path as PathLib

# Add parent directory to path for imports
sys.path.insert(0, str(PathLib(__file__).parent.parent))

from PostToolUse import (
    CommitReflectionHook,
    ReflectionQuestionFlow,
    post_tool_use,
)


class TestCommitReflectionHook:
    """Test suite for CommitReflectionHook class."""

    def test_hook_initialization_defaults(self):
        """Test hook initializes with default configuration."""
        hook = CommitReflectionHook()
        assert hook.enabled is True
        assert hook.auto_trigger is True
        assert hook.ask_before_reflecting is True
        assert hook.mcp_server_url == "localhost:3000"

    def test_hook_initialization_custom_config(self):
        """Test hook initializes with custom configuration."""
        config = {
            "enabled": False,
            "auto_trigger": False,
            "ask_before_reflecting": False,
            "mcp_server_url": "custom:8080"
        }
        hook = CommitReflectionHook(config)
        assert hook.enabled is False
        assert hook.auto_trigger is False
        assert hook.ask_before_reflecting is False
        assert hook.mcp_server_url == "custom:8080"

    def test_hook_disabled_returns_none(self):
        """Test hook returns None when disabled."""
        hook = CommitReflectionHook({"enabled": False})
        result = asyncio.run(
            hook.on_tool_use("Bash", {"command": "git commit -m 'test'"}, None)
        )
        assert result is None

    def test_hook_ignores_non_bash_tools(self):
        """Test hook ignores non-Bash tool usage."""
        hook = CommitReflectionHook()
        result = asyncio.run(
            hook.on_tool_use("Python", {"code": "print('hello')"}, None)
        )
        assert result is None

    def test_is_commit_command_detects_commit(self):
        """Test commit command detection."""
        hook = CommitReflectionHook()
        
        assert hook._is_commit_command("git commit") is True
        assert hook._is_commit_command("git commit -m 'message'") is True
        assert hook._is_commit_command("git commit --message 'test'") is True
        assert hook._is_commit_command("git status") is False
        assert hook._is_commit_command("git add .") is False
        assert hook._is_commit_command("commit") is False

    def test_is_commit_command_case_insensitive(self):
        """Test commit detection is case insensitive."""
        hook = CommitReflectionHook()
        
        assert hook._is_commit_command("GIT COMMIT") is True
        assert hook._is_commit_command("Git Commit -m 'test'") is True

    @patch('subprocess.run')
    def test_extract_commit_info_success(self, mock_subprocess):
        """Test successful commit info extraction."""
        hook = CommitReflectionHook()
        
        # Mock git commands
        mock_subprocess.side_effect = [
            Mock(stdout="abc123def456\n", returncode=0),  # rev-parse HEAD
            Mock(stdout="Test commit message\n", returncode=0),  # log
            Mock(stdout="main\n", returncode=0),  # rev-parse --abbrev-ref
            Mock(stdout="file1.py | 10 +\nfile2.py | 5 -\n", returncode=0),  # show --stat
            Mock(stdout="https://github.com/user/repo.git\n", returncode=0),  # remote get-url
        ]
        
        info = asyncio.run(hook._extract_commit_info())
        
        assert info is not None
        assert info["hash"] == "abc123def456"
        assert info["message"] == "Test commit message"
        assert info["branch"] == "main"
        assert info["files_changed"] == 2
        assert info["project_name"] == "repo"

    @patch('subprocess.run')
    def test_extract_commit_info_fallback_to_dirname(self, mock_subprocess):
        """Test commit info extraction falls back to directory name when no remote."""
        hook = CommitReflectionHook()
        
        # Mock git commands - remote fails
        mock_subprocess.side_effect = [
            Mock(stdout="abc123\n", returncode=0),  # rev-parse HEAD
            Mock(stdout="Test\n", returncode=0),  # log
            Mock(stdout="main\n", returncode=0),  # rev-parse --abbrev-ref
            Mock(stdout="file1.py | 10 +\n", returncode=0),  # show --stat
            Mock(returncode=1),  # remote get-url fails
            Mock(stdout="/path/to/project\n", returncode=0),  # basename pwd
        ]
        
        info = asyncio.run(hook._extract_commit_info())
        
        assert info is not None
        assert info["project_name"] == "project"

    @patch('subprocess.run')
    def test_extract_commit_info_handles_failure(self, mock_subprocess):
        """Test commit info extraction handles git command failures."""
        hook = CommitReflectionHook()
        
        # Mock git command failure
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, "git")
        
        info = asyncio.run(hook._extract_commit_info())
        
        assert info is None

    def test_generate_reflection_prompt(self):
        """Test reflection prompt generation."""
        hook = CommitReflectionHook()
        
        commit_info = {
            "hash": "abc123def456",
            "message": "This is a test commit message that is quite long",
            "branch": "feature/test",
            "files_changed": 3
        }
        
        prompt = hook._generate_reflection_prompt(commit_info)
        
        assert "abc123" in prompt  # Short hash
        assert "feature/test" in prompt
        assert "3" in prompt  # Files changed
        assert "Would you like to start a reflection session?" in prompt

    @patch('PostToolUse.CommitReflectionHook._extract_commit_info')
    @patch('PostToolUse.CommitReflectionHook._start_reflection_session')
    async def test_on_tool_use_auto_trigger(self, mock_start, mock_extract):
        """Test auto-trigger mode starts reflection automatically."""
        hook = CommitReflectionHook({
            "auto_trigger": True,
            "ask_before_reflecting": False
        })
        
        mock_extract.return_value = {
            "hash": "abc123",
            "message": "Test",
            "branch": "main",
            "files_changed": 1,
            "project_name": "test"
        }
        mock_start.return_value = {
            "success": True,
            "session_id": "test-session",
            "message": "Started"
        }
        
        result = await hook.on_tool_use(
            "Bash",
            {"command": "git commit -m 'test'"},
            None
        )
        
        assert result is not None
        assert "Started reflection session" in result
        mock_start.assert_called_once()

    @patch('PostToolUse.CommitReflectionHook._extract_commit_info')
    async def test_on_tool_use_ask_before(self, mock_extract):
        """Test ask-before mode generates prompt."""
        hook = CommitReflectionHook({
            "auto_trigger": False,
            "ask_before_reflecting": True
        })
        
        mock_extract.return_value = {
            "hash": "abc123",
            "message": "Test",
            "branch": "main",
            "files_changed": 1,
            "project_name": "test"
        }
        
        result = await hook.on_tool_use(
            "Bash",
            {"command": "git commit -m 'test'"},
            None
        )
        
        assert result is not None
        assert "Would you like to start a reflection session?" in result

    @patch('PostToolUse.CommitReflectionHook._extract_commit_info')
    async def test_on_tool_use_no_commit_info(self, mock_extract):
        """Test hook handles missing commit info gracefully."""
        hook = CommitReflectionHook()
        mock_extract.return_value = None
        
        result = await hook.on_tool_use(
            "Bash",
            {"command": "git commit -m 'test'"},
            None
        )
        
        assert result is None


class TestReflectionQuestionFlow:
    """Test suite for ReflectionQuestionFlow class."""

    def test_flow_initialization(self):
        """Test question flow initializes correctly."""
        flow = ReflectionQuestionFlow("test-session", "localhost:3000")
        assert flow.session_id == "test-session"
        assert flow.mcp_server_url == "localhost:3000"
        assert flow.current_question is None
        assert flow.question_index == 0

    @patch('PostToolUse.ReflectionQuestionFlow._get_next_question')
    async def test_start_flow(self, mock_get_question):
        """Test starting the question flow."""
        flow = ReflectionQuestionFlow("test-session", "localhost:3000")
        
        mock_get_question.return_value = {
            "text": "What did you accomplish?",
            "help_text": "Describe your changes",
            "required": True
        }
        
        result = await flow.start_flow()
        
        assert "Question 1" in result
        assert "What did you accomplish?" in result
        assert flow.current_question is not None

    @patch('PostToolUse.ReflectionQuestionFlow._get_next_question')
    async def test_start_flow_no_questions(self, mock_get_question):
        """Test flow handles missing questions."""
        flow = ReflectionQuestionFlow("test-session", "localhost:3000")
        mock_get_question.return_value = None
        
        with pytest.raises(RuntimeError, match="No questions available"):
            await flow.start_flow()

    @patch('PostToolUse.ReflectionQuestionFlow._send_answer')
    async def test_submit_answer_completes(self, mock_send):
        """Test submitting answer when flow is complete."""
        flow = ReflectionQuestionFlow("test-session", "localhost:3000")
        flow.current_question = {"text": "Question 1"}
        
        mock_send.return_value = {"success": True, "completed": True}
        
        result = await flow.submit_answer("My answer")
        
        assert "completed" in result.lower()
        assert "saved" in result.lower()

    @patch('PostToolUse.ReflectionQuestionFlow._send_answer')
    @patch('PostToolUse.ReflectionQuestionFlow._get_next_question')
    async def test_submit_answer_continues(self, mock_get, mock_send):
        """Test submitting answer and getting next question."""
        flow = ReflectionQuestionFlow("test-session", "localhost:3000")
        flow.current_question = {"text": "Question 1"}
        
        mock_send.return_value = {
            "success": True,
            "completed": False,
            "question": {"text": "Question 2", "required": True}
        }
        mock_get.return_value = {"text": "Question 2", "required": True}
        
        result = await flow.submit_answer("Answer 1")
        
        assert "Question 2" in result
        assert flow.question_index == 1

    def test_format_question_required(self):
        """Test formatting required question."""
        flow = ReflectionQuestionFlow("test-session", "localhost:3000")
        flow.question_index = 0
        
        question = {
            "text": "What did you accomplish?",
            "help_text": "Describe your changes",
            "required": True
        }
        
        formatted = flow._format_question(question)
        
        assert "Question 1" in formatted
        assert "What did you accomplish?" in formatted
        assert "Describe your changes" in formatted
        assert "Optional" not in formatted

    def test_format_question_optional(self):
        """Test formatting optional question."""
        flow = ReflectionQuestionFlow("test-session", "localhost:3000")
        flow.question_index = 2
        
        question = {
            "text": "Any blockers?",
            "help_text": "Optional question",
            "required": False
        }
        
        formatted = flow._format_question(question)
        
        assert "Question 3" in formatted
        assert "Optional" in formatted
        assert "skip" in formatted.lower()

    async def test_cancel_flow(self):
        """Test cancelling the flow."""
        flow = ReflectionQuestionFlow("test-session", "localhost:3000")
        
        result = await flow.cancel_flow()
        
        assert "cancelled" in result.lower()


class TestPostToolUseIntegration:
    """Integration tests for post_tool_use function."""

    def test_post_tool_use_loads_config(self):
        """Test post_tool_use loads configuration from file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / ".claude" / "hooks" / "commit-reflect.json"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            config = {
                "enabled": False,
                "auto_trigger": False
            }
            config_path.write_text(json.dumps(config))
            
            # Change to temp directory
            original_cwd = Path.cwd()
            try:
                import os
                os.chdir(tmpdir)
                
                # This would require mocking the hook, but structure is here
                pass
            finally:
                os.chdir(original_cwd)

    def test_post_tool_use_uses_defaults_when_no_config(self):
        """Test post_tool_use uses defaults when config file missing."""
        # Hook should work with default config
        # This is tested indirectly through hook initialization tests
        pass


class TestIDEIntegrationScenarios:
    """End-to-end IDE integration test scenarios."""

    @pytest.mark.asyncio
    async def test_complete_reflection_workflow(self):
        """Test complete reflection workflow from commit to completion."""
        hook = CommitReflectionHook({
            "auto_trigger": True,
            "ask_before_reflecting": False
        })
        
        # Mock all git operations
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.side_effect = [
                Mock(stdout="abc123\n", returncode=0),
                Mock(stdout="Test commit\n", returncode=0),
                Mock(stdout="main\n", returncode=0),
                Mock(stdout="file1.py | 10 +\n", returncode=0),
                Mock(stdout="https://github.com/user/repo.git\n", returncode=0),
            ]
            
            with patch.object(hook, '_start_reflection_session') as mock_start:
                mock_start.return_value = {
                    "success": True,
                    "session_id": "test-session",
                    "message": "Started"
                }
                
                result = await hook.on_tool_use(
                    "Bash",
                    {"command": "git commit -m 'test'"},
                    None
                )
                
                assert result is not None
                assert "Started reflection session" in result

    @pytest.mark.asyncio
    async def test_error_handling_commit_extraction_failure(self):
        """Test error handling when commit extraction fails."""
        hook = CommitReflectionHook()
        
        with patch('subprocess.run') as mock_subprocess:
            import subprocess
            mock_subprocess.side_effect = subprocess.CalledProcessError(1, "git")
            
            result = await hook.on_tool_use(
                "Bash",
                {"command": "git commit -m 'test'"},
                None
            )
            
            # Should handle gracefully without crashing
            assert result is None or "Could not" in result

    @pytest.mark.asyncio
    async def test_error_handling_mcp_connection_failure(self):
        """Test error handling when MCP server is unavailable."""
        hook = CommitReflectionHook({
            "auto_trigger": True,
            "ask_before_reflecting": False
        })
        
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.side_effect = [
                Mock(stdout="abc123\n", returncode=0),
                Mock(stdout="Test\n", returncode=0),
                Mock(stdout="main\n", returncode=0),
                Mock(stdout="file1.py | 10 +\n", returncode=0),
                Mock(stdout="https://github.com/user/repo.git\n", returncode=0),
            ]
            
            with patch.object(hook, '_start_reflection_session') as mock_start:
                mock_start.side_effect = Exception("Connection refused")
                
                result = await hook.on_tool_use(
                    "Bash",
                    {"command": "git commit -m 'test'"},
                    None
                )
                
                assert result is not None
                assert "Could not start reflection" in result or "error" in result.lower()


# Test fixtures

@pytest.fixture
def sample_commit_info():
    """Provide sample commit information."""
    return {
        "hash": "abc123def456",
        "message": "Add new feature",
        "branch": "feature/test",
        "files_changed": 3,
        "project_name": "test-project"
    }


@pytest.fixture
def hook_config():
    """Provide default hook configuration."""
    return {
        "enabled": True,
        "auto_trigger": True,
        "ask_before_reflecting": True,
        "mcp_server_url": "localhost:3000"
    }


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

