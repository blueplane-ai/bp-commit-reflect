# AGENTS.md

This file provides guidance to AI agents (Claude Code, Cursor, and other AI assistants) when working with code in this repository.

## Work Tracking

**IMPORTANT**: Use the `bd` command (beads issue tracker) for tracking all new work instead of markdown todo lists. Create issues for features, bugs, and tasks using:

```bash
bd create "Task description" -p <priority>
bd list                    # View open issues
bd ready                    # Show work-ready issues
bd complete <issue-id>      # Mark as done
```

See the beads documentation for full command reference. All development work should be tracked as beads issues.

## Project Overview

**Commit Reflection System** (commands: `commit-reflect`, `mcp-commit-reflect`) is a developer experience micro-journaling system that captures reflections and AI synergy assessments at commit time. It integrates seamlessly with AI-powered development workflows through CLI tools, IDE hooks, and the Model Context Protocol (MCP).

**IMPORTANT**: See [IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) for development sequencing and parallel work opportunities.

## Architecture Overview

### Three-Component Design

1. **CLI Tool** (`packages/cli/`)
   - Standalone command-line interface for capturing reflections
   - Interactive sequential question flow (5 questions)
   - Holds session state in memory until completion
   - Atomic writes to prevent partial data
   - Foundation for all other integrations

2. **MCP Server** (`packages/mcp-server/`)
   - Thin coordinator layer exposing MCP tools
   - Spawns and manages CLI processes
   - Stateless design - CLI maintains session state
   - Provides 5 tools: start_reflection, answer_question, complete, cancel, get_recent
   - Enables AI agent integration (Claude Code, Cursor)

3. **IDE Hooks** (`packages/ide-hooks/`)
   - Claude Code: PostToolUse hook detects commits
   - Cursor: afterShellExecution monitors shell commands
   - Surfaces reflection questions in chat interface
   - Communicates through MCP server

### Data Flow Architecture

The system follows a CLI-first approach with layered integrations:

```
User Interaction Points:
    Terminal (direct CLI)
    ↓
    commit-reflect --project X --commit Y
    ↓
    Interactive prompts → Storage

    AI Chat (via IDE)
    ↓
    IDE Hook detects commit
    ↓
    MCP Server spawns CLI
    ↓
    Questions surface in chat → Storage
```

### Storage Architecture

Three concurrent storage backends (configurable):

1. **JSONL** (Default, always enabled)
   - Path: `.commit-reflections.jsonl` (project root)
   - Append-only log format
   - Version-controllable, team-shareable
   - Human-readable

2. **SQLite** (Optional)
   - Path: `~/.commit-reflect/reflections.db`
   - Rich querying and analytics
   - Cross-project aggregation
   - Indexed for performance

3. **Git Commit Messages** (Optional, experimental)
   - Amends reflection to commit message body
   - Keeps data with code history
   - **WARNING**: Risky for pushed commits

### Key Data Types

See `packages/shared/types/`:
- `Reflection`: Complete reflection record with timestamp, commit info, answers
- `Question`: Question definition with type, validation, help text
- `Config`: Configuration schema for storage, questions, paths
- `Session`: MCP session state management

### Question Flow

Fixed set of 5 questions (3 required, 2 optional):
1. **AI Synergy** (1-5 scale, required)
2. **Confidence** (1-5 scale, required)
3. **Experience** (text, max 512 chars, required)
4. **Blockers** (text, optional)
5. **Learning** (text, optional)

## Common Development Commands

```bash
# Setup development environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e ".[dev]"

# Run CLI locally
cd packages/cli
python -m commit_reflect --project test --commit HEAD

# Start MCP server
cd packages/mcp-server
python -m mcp_commit_reflect

# Run tests
pytest
pytest packages/cli/tests/
pytest packages/mcp-server/tests/

# Test end-to-end flow
commit-reflect --project my-app --branch main --commit HEAD

# Multiple storage backends
commit-reflect config --storage jsonl,database --jsonl-path .reflections.jsonl
```

## Testing Philosophy

- **Unit tests** next to implementation (`test_*.py`)
- **Integration tests** for cross-package flows
- **Session tests** verify state management
- **Storage tests** ensure atomicity and consistency
- **MCP protocol tests** validate tool contracts
- **End-to-end tests** cover full workflows

Key test scenarios:
- Session timeout handling (30 minutes)
- Concurrent storage backend writes
- Process crash recovery
- Validation edge cases
- CLI-MCP communication

## Important Notes

### Development Guidelines
- **Always read IMPLEMENTATION_PLAN.md first** - it has the complete development sequencing
- Use CLI standalone before adding MCP layer
- Lock shared package interfaces early to prevent cascading changes
- Test each storage backend independently
- Ensure atomic writes - no partial reflections

### Architecture Decisions
- **ADR-001**: CLI-first approach for portability
- **ADR-002**: MCP for AI agent integration
- **ADR-003**: Multiple storage backends for flexibility
- **ADR-004**: Interactive sequential questions for better UX

### Session Management
- CLI holds all state in memory until completion
- MCP server is stateless, just coordinates
- Sessions timeout after 30 minutes of inactivity
- Cancel without saving via `cancel_reflection` tool

### Storage Best Practices
- JSONL is always enabled (safe default)
- SQLite for analytics (optional)
- Git amendment is experimental (use carefully)
- All backends write atomically on completion

## Key Files

### Documentation
- **README.md** - User-facing documentation
- **docs/ARCHITECTURE_OVERVIEW.md** - Detailed system architecture
- **docs/DIRECTORY_STRUCTURE.md** - Complete file organization
- **docs/IMPLEMENTATION_PLAN.md** - Development sequencing and parallel work
- **docs/adr/*.md** - Architecture decision records

### Core Implementation
- **packages/shared/types/** - Data models and interfaces
- **packages/shared/storage/** - Storage backend implementations
- **packages/cli/src/session.py** - Core reflection session logic
- **packages/mcp-server/src/server.py** - MCP server implementation
- **packages/ide-hooks/** - IDE integration hooks

### Configuration
- **.commit-reflect.json** - Project-level configuration
- **~/.commit-reflect/config.json** - User-level configuration
- **.config/default-questions.json** - Default question set

## When Adding Features

### Adding a New Question Type
1. Update `packages/shared/types/question.py`
2. Add validation in `packages/cli/src/validators.py`
3. Update prompting logic in `packages/cli/src/prompts.py`
4. Add tests for new question type
5. Update default configuration

### Adding a Storage Backend
1. Define interface in `packages/shared/storage/base.py`
2. Implement backend in `packages/shared/storage/`
3. Add to storage factory
4. Write comprehensive tests
5. Update configuration schema

### Adding an IDE Integration
1. Study existing hooks in `packages/ide-hooks/`
2. Detect commit operations in IDE
3. Call MCP tools for reflection flow
4. Format questions for IDE UI
5. Test end-to-end workflow

### Adding an MCP Tool
1. Define tool in `packages/mcp-server/src/tools/`
2. Register in MCP server
3. Handle in CLI with appropriate mode
4. Add protocol tests
5. Update documentation

## Development Workflow

### Phase 1: Foundation First
Start with shared types and CLI core. These block everything else.

### Phase 2: Parallel Storage
Once interfaces are stable, develop storage backends in parallel.

### Phase 3: MCP Integration
With working CLI, add MCP server as thin coordination layer.

### Phase 4: IDE Hooks
With MCP tools defined, IDE integrations can proceed independently.

### Phase 5: Polish
Documentation, packaging, and advanced features can all proceed in parallel.

## Common Issues and Solutions

### Session State
- **Problem**: Session lost on timeout
- **Solution**: 30-minute timeout is by design; data not written until completion

### Storage Failures
- **Problem**: One backend fails
- **Solution**: System continues if at least one backend succeeds (best-effort)

### Process Management
- **Problem**: MCP server loses CLI process
- **Solution**: Timeout handling and session cleanup on crash

### Git Amendment
- **Problem**: Can't amend pushed commits
- **Solution**: This is experimental; use JSONL/SQLite for pushed commits

## Debugging Tips

1. **Test CLI standalone first**: `commit-reflect --mode cli`
2. **Check MCP communication**: Enable debug logging in MCP server
3. **Verify storage**: Check both JSONL and SQLite after completion
4. **Session issues**: Look for orphaned CLI processes
5. **IDE hook problems**: Check hook installation and permissions

## Performance Considerations

- Session state held in memory (minimal footprint)
- JSONL is append-only (fast writes)
- SQLite uses indices for queries
- MCP server spawns one CLI process per session
- 30-minute timeout prevents resource leaks

## Security Notes

- JSONL files may be committed to repos (consider .gitignore)
- SQLite database is user-local by default
- No network communication required (all local)
- Git amendment requires appropriate permissions
- Consider data privacy when sharing reflections