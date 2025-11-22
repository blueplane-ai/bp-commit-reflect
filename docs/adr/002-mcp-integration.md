# ADR-002: Model Context Protocol Integration

## Status

Accepted

## Context

AI-powered development tools (Claude Code, Cursor, etc.) are becoming primary development environments for many developers. We need a way to integrate commit reflections into these AI-driven workflows without:

1. Interrupting the developer's flow with external tools
2. Building custom integrations for each IDE/AI platform
3. Maintaining IDE-specific code for core reflection logic

The Model Context Protocol (MCP) is an emerging standard for AI agent tool integration, supported by Anthropic and other AI platforms. We need to decide how to expose commit reflection capabilities to AI agents.

Key requirements:
- Enable AI agents to trigger reflection sessions
- Surface reflection questions naturally in chat interfaces
- Support multi-turn conversational reflection gathering
- Work across multiple AI platforms (Claude Code, Cursor, future tools)
- Maintain separation between AI integration and core logic

## Decision

We will build an MCP server (`mcp-commit-reflect`) that exposes commit reflection capabilities as MCP tools. The MCP server will act as a stateless coordinator that spawns and manages CLI processes for actual reflection logic.

**MCP Tools Provided:**
- `start_commit_reflection` - Initialize session and return first question
- `answer_reflection_question` - Submit answer and get next question
- `complete_reflection` - Finalize and persist reflection data
- `cancel_reflection` - Abort session without saving
- `get_recent_reflections` - Query historical reflections

**Architecture:**
```
AI Agent (Claude Code, Cursor, etc.)
    ↓ MCP tool calls
MCP Server (stateless coordinator)
    ↓ spawn/manage
CLI Process (maintains in-memory session state)
    ↓ write on completion
Storage Backends (JSONL, SQLite, git)
```

## Consequences

### Positive

- **Cross-platform compatibility**: Single MCP server works with any MCP-compatible AI agent
- **Conversational UX**: Reflection questions surface naturally in chat, feeling like conversation with AI
- **Future-proof**: As MCP adoption grows, system automatically works with new tools
- **Standard protocol**: Uses industry-standard interface rather than proprietary APIs
- **Separation of concerns**: MCP server focuses on protocol translation, CLI handles logic
- **Ecosystem integration**: Enables other Blueplane tools to interact via same protocol
- **Agent-friendly**: AI agents can access historical reflections for context-aware suggestions

### Negative

- **MCP adoption risk**: If MCP doesn't achieve widespread adoption, effort may be wasted
- **Additional component**: Requires running MCP server process in addition to CLI
- **Process coordination overhead**: MCP server must spawn and track CLI processes
- **Protocol complexity**: MCP adds learning curve for contributors
- **Session management**: Must handle session timeouts, crashes, and cleanup

### Neutral

- **IDE hook dependency**: IDE hooks (Claude Code, Cursor) still needed to detect commits and trigger MCP calls
- **Installation complexity**: Users must configure MCP server in their AI tool settings
- **Versioning**: MCP server and CLI versions should be synchronized

## Alternatives Considered

### Direct IDE Extension APIs

Build native extensions for each IDE using their extension APIs.

**Pros:**
- Tighter IDE integration
- No additional process/server
- Access to full IDE capabilities

**Cons:**
- Must rewrite for each IDE (VS Code, JetBrains, Cursor, etc.)
- IDE-specific APIs constantly change
- Higher maintenance burden
- Vendor lock-in to specific IDEs
- Can't support terminal-only workflows

### Custom HTTP API

Build a proprietary HTTP API for AI agents to call.

**Pros:**
- Simple HTTP/REST interface
- Language agnostic
- Could add web dashboard

**Cons:**
- Requires running web server
- Not a standard protocol
- Each AI tool needs custom integration
- Overkill for local-only tool
- Security concerns with HTTP endpoints

### IDE Chat Commands Only

Implement as slash commands or chat commands in each IDE without MCP.

**Pros:**
- Simple implementation
- No additional server process
- Direct IDE integration

**Cons:**
- Duplicated code per IDE
- Can't leverage AI agent capabilities (context, parsing, conversation flow)
- Less natural conversational experience
- Limited to IDEs that support custom commands

### Python-based MCP SDK

Use Python MCP SDK instead of Node.js/TypeScript.

**Pros:**
- Python MCP SDK is well-documented
- Strong data processing libraries
- Good CLI tooling ecosystem

**Cons:**
- Creates language mismatch with likely Node.js/TypeScript CLI
- Harder for JavaScript developers to contribute
- Python deployment/versioning complexity
- Node.js more common in developer tooling

## References

- [Model Context Protocol Documentation](https://modelcontextprotocol.io/)
- [Anthropic MCP Announcement](https://www.anthropic.com/news/model-context-protocol)
- [MCP TypeScript SDK](https://github.com/anthropics/mcp-typescript-sdk)
- ADR-001: CLI-First Architecture
