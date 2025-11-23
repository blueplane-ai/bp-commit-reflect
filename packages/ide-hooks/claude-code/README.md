# Claude Code Hook for Commit Reflection

PostToolUse hook that automatically detects git commits and triggers reflection sessions.

## Features

- **Automatic Detection**: Monitors Bash tool usage for `git commit` commands
- **Interactive Flow**: Presents reflection questions in Claude Code chat
- **Context Preservation**: Maintains conversation flow during reflection
- **Configurable**: Control when and how reflections are triggered
- **MCP Integration**: Communicates with MCP server for session management

## Installation

1. Copy `PostToolUse.py` to your Claude Code hooks directory:
   ```bash
   cp PostToolUse.py ~/.claude/hooks/
   ```

2. Create configuration file (optional):
   ```bash
   mkdir -p .claude/hooks
   cat > .claude/hooks/commit-reflect.json << EOF
   {
     "enabled": true,
     "auto_trigger": false,
     "ask_before_reflecting": true,
     "mcp_server_url": "localhost:3000"
   }
   EOF
   ```

## Configuration

Create `.claude/hooks/commit-reflect.json`:

```json
{
  "enabled": true,
  "auto_trigger": false,
  "ask_before_reflecting": true,
  "mcp_server_url": "localhost:3000"
}
```

### Options

- **enabled** (default: true): Enable/disable the hook
- **auto_trigger** (default: true): Automatically start reflection after commit
- **ask_before_reflecting** (default: true): Ask before starting reflection
- **mcp_server_url** (default: "localhost:3000"): MCP server URL

## How It Works

1. **Commit Detection**: Hook monitors Bash tool for git commit commands
2. **Info Extraction**: Extracts commit hash, message, branch, and stats
3. **User Prompt**: Asks if user wants to reflect (if configured)
4. **Session Start**: Initiates reflection via MCP server
5. **Question Flow**: Presents questions sequentially in chat
6. **Completion**: Saves reflection when all questions answered

## Usage Flow

### Automatic Mode (auto_trigger: true)

```
User: git commit -m "Add user authentication"
Claude: [Executes commit]
Hook: 📝 Started reflection session for commit abc12345.
      I'll ask you some questions about this commit.

      Question 1: What did you accomplish in this commit?
User: [Answers questions...]
Claude: ✅ Reflection completed! Your insights have been saved.
```

### Manual Mode (ask_before_reflecting: true)

```
User: git commit -m "Add user authentication"
Claude: [Executes commit]
Hook: 📝 Commit Reflection

      I noticed you just made a commit:
      - Commit: abc12345
      - Branch: main
      - Message: "Add user authentication"

      Would you like to reflect on this commit?
User: yes
Claude: Great! Let's reflect on this commit.
        Question 1: What did you accomplish?
```

## Development

### Testing

```python
import asyncio
from PostToolUse import CommitReflectionHook

async def test_hook():
    hook = CommitReflectionHook({
        "enabled": True,
        "auto_trigger": False,
    })

    result = await hook.on_tool_use(
        "Bash",
        {"command": "git commit -m 'test'"},
        None
    )

    print(result)

asyncio.run(test_hook())
```

### Architecture

- **CommitReflectionHook**: Main hook class that detects commits
- **ReflectionQuestionFlow**: Manages the interactive question flow
- **post_tool_use()**: Entry point called by Claude Code

### Integration Points

1. **Tool Monitoring**: Listens to Bash tool usage
2. **Git Integration**: Extracts commit metadata via git commands
3. **MCP Communication**: Calls MCP server for session management
4. **Chat Formatting**: Formats questions for Claude Code UI

## Troubleshooting

### Hook Not Triggering

- Check that hook is in the correct location: `~/.claude/hooks/PostToolUse.py`
- Verify hook is enabled in configuration
- Check Claude Code logs for errors

### MCP Server Connection Issues

- Ensure MCP server is running: `mcp-commit-reflect`
- Verify `mcp_server_url` in configuration
- Check network connectivity

### Git Command Failures

- Ensure git is installed and in PATH
- Verify you're in a git repository
- Check git configuration

## Future Enhancements

- Support for batch commit reflections
- Integration with GitHub/GitLab for PR context
- Team reflection aggregation
- Custom question sets per project
- Reflection templates and presets
