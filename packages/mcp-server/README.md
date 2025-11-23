# MCP Server for Commit Reflection System

Model Context Protocol (MCP) server that coordinates commit reflection sessions via CLI processes.

## Features

- **Session Management**: Handles multiple concurrent reflection sessions
- **Process Coordination**: Spawns and manages CLI processes for each session
- **Timeout Handling**: Automatically cleans up stale sessions
- **Graceful Shutdown**: Properly terminates all sessions on shutdown
- **MCP Tools**: Provides 5 core tools for AI agent integration

## MCP Tools

1. **start_reflection** - Initialize a new reflection session
2. **answer_question** - Answer a reflection question
3. **complete_reflection** - Complete and save the reflection
4. **cancel_reflection** - Cancel an active session
5. **get_recent_reflections** - Query recent reflections

## Usage

```python
from mcp_commit_reflect import MCPReflectionServer

# Create and start server
server = MCPReflectionServer(
    max_concurrent_sessions=10,
    session_timeout=1800,  # 30 minutes
    cleanup_interval=300,  # 5 minutes
)

await server.start()

# Use MCP tools
result = await server.start_reflection(
    commit_hash="abc123",
    project_name="my-project",
    branch="main"
)

session_id = result["session_id"]

# Answer questions
await server.answer_question(
    session_id=session_id,
    answer="Implemented user authentication"
)

# Complete reflection
await server.complete_reflection(session_id=session_id)

# Stop server
await server.stop()
```

## Configuration

- `max_concurrent_sessions`: Maximum number of active sessions (default: 10)
- `session_timeout`: Session timeout in seconds (default: 1800)
- `cleanup_interval`: How often to clean up stale sessions (default: 300)
- `cli_command`: Command to execute for CLI processes (default: "commit-reflect")

## Architecture

The MCP server is stateless - all session state is maintained by the SessionManager, and the actual reflection logic runs in CLI processes. This design ensures:

- Clean separation of concerns
- Easy testing and debugging
- Process isolation for safety
- Simple recovery from crashes
