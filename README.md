# Commit Reflection System

A developer experience micro-journaling system that captures reflections and AI synergy assessments at commit time, integrating seamlessly with AI-powered development workflows through CLI tools, IDE hooks, and the Model Context Protocol (MCP).

## Overview

The Commit Reflection System helps developers capture meaningful insights about their work at the moment of committing code. By prompting for quick reflections on AI collaboration quality, confidence levels, experience notes, blockers, and learning moments, it creates a valuable historical record of the development process.

Designed as a modular component within the Blueplane ecosystem, this system provides:

- **Standalone CLI tool** for direct command-line usage
- **MCP server** for integration with AI agents (Claude Code, Cursor, etc.)
- **IDE hooks** for seamless in-editor reflection capture
- **Multiple storage backends** (JSONL, SQLite database, git commit messages)
- **Rich querying and analytics** capabilities

## Architecture

The system consists of three main components:

### 1. CLI Tool: `commit-reflect`

Standalone command-line interface for capturing developer experience data post-commit.

```bash
commit-reflect --project <project-name> --branch <branch-name> --commit <hash>
commit-reflect --project <project-name> --branch <branch-name> --commits <hash1,hash2,hash3>
```

**Features:**
- Interactive one-by-one question prompting
- Configurable question sets via JSON config
- Multiple storage backends (JSONL, SQLite database, amended commit messages)
- Progress indicators and helpful context

### 2. MCP Server: `mcp-commit-reflect`

Exposes commit reflection capabilities to AI agents through the Model Context Protocol.

**MCP Tools:**
- `start_commit_reflection` - Initialize a new reflection session
- `answer_reflection_question` - Submit answers and advance to next question
- `complete_reflection` - Finalize and save the reflection
- `cancel_reflection` - Cancel without saving
- `get_recent_reflections` - Retrieve historical data

### 3. IDE Integration Hooks

**Claude Code:** PostToolUse hook that detects git commits and surfaces reflection prompts in chat

**Cursor:** afterShellExecution hook that monitors shell commands for commits

## Quick Start

### Installation

```bash
# Install the CLI tool
pip install commit-reflect

# Install the MCP server
pip install mcp-commit-reflect
```

### Basic Usage

```bash
# Capture a reflection for the latest commit
commit-reflect --project my-app --branch main --commit HEAD

# Configure your storage preferences
commit-reflect config --storage jsonl,database --jsonl-path .reflections.jsonl
```

### IDE Integration

#### Claude Code

Add to `.claude/hooks/post-tool-use.py`:

```python
# See packages/ide-hooks/claude-code/post_tool_use.py for full implementation
async def on_post_tool_use(tool_name, tool_input, tool_output):
    # Detects commits and triggers MCP-based reflection
    pass
```

#### Cursor

Add to `.cursor/hooks/after_shell_execution.py`:

```python
# See packages/ide-hooks/cursor/after_shell_execution.py for full implementation
async def after_shell_execution(command, output, exit_code):
    # Monitors git commits and triggers reflection prompts
    pass
```

## Question Set

The default reflection includes:

1. **AI Synergy** (scale 1-5) - Required
   - How well did you and AI work together on this commit?

2. **Confidence** (scale 1-5) - Required
   - How confident are you in these changes?

3. **Experience** (text, max 512 chars) - Required
   - How did this work feel? What was the experience like?

4. **Blockers** (text) - Optional
   - What blockers or friction did you encounter?

5. **Learning** (text) - Optional
   - What did you learn from this work?

Questions are fully configurable via the config file.

## Data Storage

### JSONL Format

Each reflection is stored as a single-line JSON object:

```json
{
  "timestamp": "2025-11-22T10:30:00Z",
  "project": "my-web-app",
  "branch": "feature/user-auth",
  "commit_hash": "a1b2c3d4",
  "commit_message": "Add JWT authentication middleware",
  "files_changed": ["src/auth/middleware.py", "tests/test_auth.py"],
  "reflections": {
    "ai_synergy": 4,
    "confidence": 5,
    "experience": "Felt smooth once I got into it...",
    "blockers": "Unclear documentation on refresh token storage...",
    "learning": "Learned about HttpOnly cookies..."
  },
  "metadata": {
    "session_duration_minutes": 45,
    "lines_added": 127,
    "lines_removed": 12
  }
}
```

### SQLite Database

Structured storage using SQLite enabling rich queries:

```sql
SELECT AVG(ai_synergy) as avg_synergy,
       AVG(confidence) as avg_confidence,
       COUNT(*) as total_commits
FROM reflections
WHERE project = 'my-app'
  AND timestamp > datetime('now', '-7 days');
```

## Configuration

Create `.commit-reflect.json` in your project root or `~/.commit-reflect/config.json`:

```json
{
  "storage": ["jsonl", "database"],
  "jsonl_path": ".commit-reflections.jsonl",
  "db_path": "~/.commit-reflect/reflections.db",
  "questions": [
    {
      "id": "ai_synergy",
      "prompt": "How well did you and AI work together on this?",
      "type": "scale",
      "range": [1, 5],
      "optional": false,
      "help_text": "1 = AI hindered progress, 5 = Perfect collaboration"
    }
    // ... more questions
  ]
}
```

## Project Structure

```
ai-commit-reflect/
├── packages/
│   ├── cli/                    # Standalone CLI tool (Python)
│   │   └── src/
│   ├── mcp-server/             # Model Context Protocol server (Python)
│   │   └── src/
│   ├── ide-hooks/              # IDE integration hooks (Python)
│   │   ├── claude-code/
│   │   └── cursor/
│   └── shared/                 # Shared types and utilities (Python)
│       ├── types/
│       └── storage/
├── docs/
│   └── adr/                    # Architecture Decision Records
├── examples/                   # Example configurations and usage
├── tests/                      # Test suites
└── .config/                    # Default configuration templates
```

## Implementation Roadmap

### Phase 1: Core CLI Tool
- Standalone CLI with basic prompts
- JSONL storage
- SQLite database storage
- Configuration file support
- Question templates

### Phase 2: MCP Server
- MCP server with core tools
- Claude Code integration testing
- Session management
- Reflection retrieval

### Phase 3: IDE Hooks
- Claude Code PostToolUse hook
- Cursor afterShellExecution hook
- End-to-end workflow testing
- UX refinement

## Blueplane Ecosystem Integration

This commit reflection system is designed as a self-contained, modular component within the broader Blueplane ecosystem:

- **Data portability:** JSONL and SQLite outputs can be consumed by other Blueplane tools
- **Modular architecture:** Each component operates independently
- **Ecosystem interoperability:** Structured data formats enable seamless integration
- **Extensibility:** MCP interface provides standard protocol for future components

## Development

### Prerequisites

- Python 3.9+
- Git
- SQLite (included with Python)

### Setup

```bash
# Clone the repository
git clone https://github.com/blueplane-ai/ai-commit-reflect.git
cd ai-commit-reflect

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

### Running Locally

```bash
# Run CLI in development mode
cd packages/cli
python -m commit_reflect --project test --branch main --commit HEAD

# Start MCP server
cd packages/mcp-server
python -m mcp_commit_reflect
```

## License

See [LICENSE](LICENSE) file for details.

## Architecture Decision Records

Key design decisions are documented in [docs/adr/](docs/adr/):

- [ADR-001: CLI-First Architecture](docs/adr/001-cli-first-architecture.md)
- [ADR-002: Model Context Protocol Integration](docs/adr/002-mcp-integration.md)
- [ADR-003: Multiple Storage Backends](docs/adr/003-multiple-storage-backends.md)
- [ADR-004: Interactive Sequential Question Flow](docs/adr/004-interactive-question-flow.md)

## Support

For questions, issues, or feature requests, please open an issue on GitHub.
