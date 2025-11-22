# ADR-001: CLI-First Architecture

## Status

Accepted

## Context

The Commit Reflection System needs to capture developer reflections at commit time across multiple environments (standalone terminal, IDE integrations, AI agent workflows). We need to decide whether to:

1. Build IDE-specific implementations first and extract common logic later
2. Build a web service that all clients connect to
3. Build a standalone CLI tool as the foundation

Key requirements:
- Must work in terminal environments without IDE
- Must be testable in isolation
- Must be portable across different deployment scenarios
- Should minimize external dependencies
- Should enable git hook integration
- Should serve as foundation for more complex integrations

## Decision

We will build a standalone CLI tool (`commit-reflect`) as the foundational component of the system, with all other integrations (MCP server, IDE hooks) built on top of it.

The CLI will:
- Accept commit context via command-line arguments
- Implement all core reflection logic (prompting, validation, storage)
- Support multiple storage backends
- Be usable independently without any IDE or MCP server
- Serve as the execution engine that MCP server coordinates

## Consequences

### Positive

- **Testability**: CLI can be tested in isolation without complex IDE or MCP setup
- **Portability**: Works in any environment with Node.js/shell access
- **Git hook integration**: Can be called directly from git hooks (post-commit, pre-push, etc.)
- **Debugging**: Easy to debug and troubleshoot without IDE dependencies
- **Standalone value**: Provides immediate value to developers who prefer terminal workflows
- **Foundation for integrations**: MCP server and IDE hooks become thin wrappers around CLI
- **CI/CD friendly**: Can be integrated into automation pipelines
- **Documentation**: Easier to document and provide examples for CLI than complex integrations

### Negative

- **Performance overhead**: MCP server spawning CLI processes adds overhead vs native implementation
- **Process management**: MCP server must manage CLI process lifecycle
- **Inter-process communication**: Requires careful handling of stdin/stdout/stderr
- **Duplicate installations**: Users need both CLI and MCP server (though MCP can bundle CLI)

### Neutral

- **Two installation targets**: Users may install just CLI, or CLI + MCP server
- **Version synchronization**: MCP server version should match CLI version
- **Learning curve**: Developers must understand both CLI and MCP layers for debugging

## Alternatives Considered

### IDE-Native Implementations

Build reflection logic directly into each IDE hook (Claude Code, Cursor) as separate implementations.

**Pros:**
- No process spawning overhead
- Tighter integration with IDE features
- Potentially better performance

**Cons:**
- Code duplication across IDE implementations
- No standalone usage without IDE
- Harder to test in isolation
- Can't be used in git hooks or CI/CD
- Maintenance burden across multiple codebases
- No terminal-only workflow support

### Web Service Architecture

Build a centralized HTTP service that all clients (CLI, IDE, MCP) connect to.

**Pros:**
- Single source of truth for reflection logic
- Centralized data storage
- Could enable team-wide analytics easily
- Thin clients

**Cons:**
- Requires network connectivity
- Additional infrastructure to deploy and maintain
- Latency in reflection workflow
- Privacy/security concerns with centralized data
- Overkill for single-developer use case
- Harder to run in air-gapped environments

### Library-Only Approach

Create a shared npm package with reflection logic, imported by each integration point.

**Pros:**
- Code reuse through imports
- No process spawning
- Lightweight

**Cons:**
- No standalone CLI usage
- Requires Node.js runtime in every integration
- Can't be used from git hooks without wrapper script
- Less flexible for non-JavaScript integrations

## References

- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [Unix Philosophy: Small, Composable Tools](https://en.wikipedia.org/wiki/Unix_philosophy)
- Original system architecture outline
