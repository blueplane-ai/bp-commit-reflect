"""
Claude Code PostToolUse hook for commit reflection.

This hook detects when commits are made via Claude Code and automatically
triggers the reflection flow by communicating with the MCP server.
"""

import json
import logging
import re
import subprocess
from typing import Any

logger = logging.getLogger(__name__)


class CommitReflectionHook:
    """
    Claude Code hook that detects commits and triggers reflections.

    This hook monitors Bash tool usage for git commit commands and
    initiates a reflection session through the MCP server.
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize the commit reflection hook.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self.auto_trigger = self.config.get("auto_trigger", True)
        self.ask_before_reflecting = self.config.get("ask_before_reflecting", True)
        self.mcp_server_url = self.config.get("mcp_server_url", "localhost:3000")

        # Patterns to detect git commit commands
        self.commit_patterns = [
            r"git\s+commit",
            r"git\s+commit\s+-m",
            r"git\s+commit\s+--message",
        ]

    async def on_tool_use(
        self, tool_name: str, tool_input: dict[str, Any], tool_result: Any
    ) -> str | None:
        """
        Hook called after a tool is used.

        Args:
            tool_name: Name of the tool that was used
            tool_input: Input parameters to the tool
            tool_result: Result returned by the tool

        Returns:
            Optional message to append to conversation
        """
        if not self.enabled:
            return None

        # Only monitor Bash tool
        if tool_name != "Bash":
            return None

        # Check if this was a git commit command
        command = tool_input.get("command", "")
        if not self._is_commit_command(command):
            return None

        # Extract commit info
        commit_info = await self._extract_commit_info()
        if not commit_info:
            logger.warning("Could not extract commit information")
            return None

        logger.info(f"Detected commit: {commit_info['hash'][:8]}")

        # If auto-trigger is disabled or we should ask first, return a prompt
        if not self.auto_trigger or self.ask_before_reflecting:
            return self._generate_reflection_prompt(commit_info)

        # Auto-trigger reflection
        try:
            await self._start_reflection_session(commit_info)
            return f"\n\n📝 Started reflection session for commit {commit_info['hash'][:8]}. I'll ask you some questions about this commit."
        except Exception as e:
            logger.error(f"Failed to start reflection: {e}")
            return f"\n\n⚠️ Could not start reflection session: {e}"

    def _is_commit_command(self, command: str) -> bool:
        """
        Check if a command is a git commit.

        Args:
            command: Shell command to check

        Returns:
            True if this is a commit command
        """
        for pattern in self.commit_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return True
        return False

    async def _extract_commit_info(self) -> dict[str, Any] | None:
        """
        Extract information about the most recent commit.

        Returns:
            Dictionary with commit info or None if extraction fails
        """
        try:
            # Get latest commit hash
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
            )
            commit_hash = result.stdout.strip()

            # Get commit message
            result = subprocess.run(
                ["git", "log", "-1", "--pretty=%B"], capture_output=True, text=True, check=True
            )
            commit_message = result.stdout.strip()

            # Get branch name
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            )
            branch = result.stdout.strip()

            # Get commit stats
            result = subprocess.run(
                ["git", "show", "--stat", "--pretty=format:", commit_hash],
                capture_output=True,
                text=True,
                check=True,
            )
            stats = result.stdout.strip()

            # Parse stats for file counts
            files_changed = len(
                [line for line in stats.split("\n") if line.strip() and "|" in line]
            )

            # Get project name from git remote or directory
            project_name = None
            try:
                result = subprocess.run(
                    ["git", "remote", "get-url", "origin"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                remote_url = result.stdout.strip()
                # Extract project name from URL
                if remote_url:
                    project_name = remote_url.rstrip("/").split("/")[-1].replace(".git", "")
            except subprocess.CalledProcessError:
                # No remote, use directory name
                result = subprocess.run(
                    [
                        "basename",
                        subprocess.run(["pwd"], capture_output=True, text=True).stdout.strip(),
                    ],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                project_name = result.stdout.strip()

            return {
                "hash": commit_hash,
                "message": commit_message,
                "branch": branch,
                "files_changed": files_changed,
                "project_name": project_name,
            }

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to extract commit info: {e}")
            return None

    def _generate_reflection_prompt(self, commit_info: dict[str, Any]) -> str:
        """
        Generate a prompt asking if user wants to reflect.

        Args:
            commit_info: Information about the commit

        Returns:
            Formatted prompt string
        """
        commit_hash_short = commit_info["hash"][:8]
        message_preview = commit_info["message"][:60]
        if len(commit_info["message"]) > 60:
            message_preview += "..."

        return f"""

📝 **Commit Reflection**

I noticed you just made a commit:
- Commit: `{commit_hash_short}`
- Branch: `{commit_info['branch']}`
- Message: "{message_preview}"
- Files changed: {commit_info['files_changed']}

Would you like to reflect on this commit? I can ask you a few questions to capture:
- What you accomplished
- How confident you feel about the changes
- Any challenges you faced
- What you learned
- Next steps

This reflection will be saved alongside your commit for future reference.

Would you like to start a reflection session? (yes/no)
"""

    async def _start_reflection_session(self, commit_info: dict[str, Any]) -> dict[str, Any]:
        """
        Start a reflection session via MCP server.

        Args:
            commit_info: Information about the commit

        Returns:
            Session information from MCP server
        """
        # In a real implementation, this would call the MCP server
        # For now, return a mock response
        logger.info(f"Starting reflection for commit {commit_info['hash'][:8]}")

        # This would be an actual MCP call:
        # async with aiohttp.ClientSession() as session:
        #     async with session.post(
        #         f"http://{self.mcp_server_url}/start_reflection",
        #         json={
        #             "commit_hash": commit_info["hash"],
        #             "project_name": commit_info["project_name"],
        #             "branch": commit_info["branch"],
        #         }
        #     ) as response:
        #         return await response.json()

        return {"success": True, "session_id": "mock-session-id", "message": "Reflection started"}


class ReflectionQuestionFlow:
    """
    Manages the interactive question flow in Claude Code chat.

    Handles presenting questions, collecting answers, and coordinating
    with the MCP server to complete the reflection.
    """

    def __init__(self, session_id: str, mcp_server_url: str):
        """
        Initialize the question flow.

        Args:
            session_id: Session ID from MCP server
            mcp_server_url: URL of the MCP server
        """
        self.session_id = session_id
        self.mcp_server_url = mcp_server_url
        self.current_question = None
        self.question_index = 0

    async def start_flow(self) -> str:
        """
        Start the question flow.

        Returns:
            First question formatted for chat
        """
        # Get first question from MCP server
        self.current_question = await self._get_next_question()

        if not self.current_question:
            raise RuntimeError("No questions available")

        return self._format_question(self.current_question)

    async def submit_answer(self, answer: str) -> str | None:
        """
        Submit an answer and get the next question.

        Args:
            answer: User's answer to current question

        Returns:
            Next question or None if complete
        """
        # Send answer to MCP server
        result = await self._send_answer(answer)

        if result.get("completed"):
            return "✅ Reflection completed! Your insights have been saved."

        # Get next question
        self.current_question = result.get("question")
        self.question_index += 1

        if not self.current_question:
            return None

        return self._format_question(self.current_question)

    async def cancel_flow(self) -> str:
        """
        Cancel the reflection flow.

        Returns:
            Cancellation message
        """
        # Call MCP server to cancel
        logger.info(f"Cancelling reflection session {self.session_id}")

        return "Reflection cancelled. No worries, you can reflect on commits anytime!"

    def _format_question(self, question: dict[str, Any]) -> str:
        """
        Format a question for display in chat.

        Args:
            question: Question data from MCP server

        Returns:
            Formatted question string
        """
        question_text = question.get("text", "")
        help_text = question.get("help_text", "")
        required = question.get("required", True)

        formatted = f"\n**Question {self.question_index + 1}**\n\n"
        formatted += f"{question_text}\n"

        if help_text:
            formatted += f"\n*{help_text}*\n"

        if not required:
            formatted += "\n*(Optional - you can skip this question)*\n"

        return formatted

    async def _get_next_question(self) -> dict[str, Any] | None:
        """
        Get the next question from MCP server.

        Returns:
            Question data or None
        """
        # Mock implementation
        return {
            "text": "What did you accomplish in this commit?",
            "help_text": "Describe the changes you made and why",
            "required": True,
        }

    async def _send_answer(self, answer: str) -> dict[str, Any]:
        """
        Send answer to MCP server.

        Args:
            answer: User's answer

        Returns:
            Response from server
        """
        # Mock implementation
        return {
            "success": True,
            "completed": False,
            "question": {
                "text": "On a scale of 1-5, how confident are you about these changes?",
                "help_text": "1 = Not confident, 5 = Very confident",
                "required": True,
            },
        }


# Hook registration for Claude Code
async def post_tool_use(tool_name: str, tool_input: dict[str, Any], tool_result: Any) -> str | None:
    """
    Claude Code hook entry point.

    Args:
        tool_name: Name of the tool that was used
        tool_input: Input parameters to the tool
        tool_result: Result returned by the tool

    Returns:
        Optional message to append to conversation
    """
    # Load configuration from .claude/hooks/commit-reflect.json
    config = {}
    try:
        with open(".claude/hooks/commit-reflect.json") as f:
            config = json.load(f)
    except FileNotFoundError:
        pass  # Use defaults

    hook = CommitReflectionHook(config)
    return await hook.on_tool_use(tool_name, tool_input, tool_result)
