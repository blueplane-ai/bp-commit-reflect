# Commit Reflection System - User Guide

Welcome to the Commit Reflection System! This guide will help you get started with capturing meaningful reflections about your commits.

## Table of Contents

- [What is Commit Reflection?](#what-is-commit-reflection)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Usage](#usage)
- [IDE Integration](#ide-integration)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## What is Commit Reflection?

The Commit Reflection System helps you capture valuable context and insights about your commits through a guided reflection process. Instead of losing important context about *why* changes were made and *what* you learned, this system prompts you to record these insights immediately after committing.

### Benefits

- **Preserve context** - Capture the reasoning behind changes while it's fresh
- **Learn faster** - Reflect on what worked, what didn't, and what you learned
- **Better code reviews** - Provide rich context for reviewers
- **Knowledge sharing** - Help future developers (including future you) understand decisions
- **AI-assisted development** - Help AI assistants understand your codebase better

## Installation

### Prerequisites

- Python 3.9 or higher
- Git

### Install from PyPI

```bash
pip install commit-reflect
```

### Install from source

```bash
git clone https://github.com/yourusername/commit-reflect.git
cd commit-reflect
pip install -e packages/shared
```

### Verify installation

```bash
commit-reflect --version
```

## Quick Start

### 1. Initialize in your repository

```bash
cd your-project
commit-reflect init
```

This creates a default configuration file at `.config/commit-reflect.json`.

### 2. Make a commit

```bash
git add .
git commit -m "Add user authentication"
```

### 3. Start reflection (manual mode)

```bash
commit-reflect reflect
```

The system will guide you through a series of questions about your commit:

```
🔍 Commit Reflection Session
Commit: abc123d "Add user authentication"
Files changed: 5 files (+150, -20)

❓ What changed in this commit?
> Added JWT-based authentication system with login and logout endpoints

❓ Why was this change necessary?
> Users needed secure session management for the API

❓ How was this implemented?
> Implemented JWT tokens with RS256 signing, 1-hour expiry

... (continue with remaining questions)

✅ Reflection saved successfully!
```

### 4. View your reflections

```bash
# List all reflections
commit-reflect list

# Show specific reflection
commit-reflect show abc123d

# Export reflections
commit-reflect export --format json > reflections.json
```

## Configuration

### Configuration File Locations

The system searches for configuration in this order:

1. `./.config/commit-reflect.json` (project-local)
2. `~/.commit-reflect/config.json` (user-global)
3. `/etc/commit-reflect/config.json` (system-wide)

### Basic Configuration

Create `.config/commit-reflect.json`:

```json
{
  "version": "1.0",
  "storage": {
    "backends": [
      {
        "type": "jsonl",
        "path": ".commit-reflections.jsonl"
      }
    ]
  },
  "questions": [
    {
      "id": "what",
      "text": "What changed?",
      "type": "text",
      "required": true
    },
    {
      "id": "why",
      "text": "Why was this necessary?",
      "type": "text",
      "required": true
    }
  ]
}
```

### Configuration Options

See [examples/README.md](../examples/README.md) for complete configuration examples.

## Usage

### CLI Commands

#### Start a reflection

```bash
# Reflect on the most recent commit
commit-reflect reflect

# Reflect on a specific commit
commit-reflect reflect abc123d

# Interactive mode with prompts
commit-reflect reflect --interactive
```

#### List reflections

```bash
# List all reflections
commit-reflect list

# List recent reflections
commit-reflect list --limit 10

# Filter by date
commit-reflect list --since "2024-01-01"
commit-reflect list --until "2024-01-31"

# Filter by author
commit-reflect list --author "john@example.com"
```

#### Show reflection details

```bash
# Show full reflection
commit-reflect show abc123d

# Show as JSON
commit-reflect show abc123d --json

# Show with git diff
commit-reflect show abc123d --with-diff
```

#### Export reflections

```bash
# Export as JSON
commit-reflect export --format json > reflections.json

# Export as CSV
commit-reflect export --format csv > reflections.csv

# Export specific date range
commit-reflect export --since "2024-01-01" --format json
```

#### Validate configuration

```bash
# Validate default config
commit-reflect validate-config

# Validate specific file
commit-reflect validate-config custom-config.json
```

### MCP Server Mode

For IDE integration, run as MCP server:

```bash
commit-reflect mcp-server
```

See [IDE Integration](#ide-integration) for details.

## IDE Integration

### Claude Code Integration

1. Install the hook in your `.claude/hooks/PostToolUse.md`:

```markdown
# Post Tool Use Hook

When a git commit is detected:
1. Start reflection session via MCP
2. Present questions in chat
3. Collect answers conversationally
4. Save reflection
```

2. The hook automatically triggers after git commits made through Claude Code.

### Cursor Integration

1. Configure in `.cursor/settings.json`:

```json
{
  "afterShellExecution": {
    "patterns": ["git commit"],
    "handler": "commit-reflect-mcp"
  }
}
```

2. Reflections trigger automatically after git commits.

## Best Practices

### Writing Effective Reflections

**Good reflection:**
```
What: Added JWT authentication with refresh tokens
Why: Users needed persistent sessions without storing passwords
How: RS256 tokens (1hr access, 7d refresh), implemented token rotation
Challenges: Handled concurrent login race conditions with distributed locks
Learnings: JWT rotation strategies, Redis distributed locking patterns
```

**Poor reflection:**
```
What: Fixed auth
Why: It was broken
How: Made it work
```

### Tips

1. **Be specific** - Include technical details, not just summaries
2. **Explain trade-offs** - Why this approach over alternatives?
3. **Record challenges** - What problems did you encounter and how did you solve them?
4. **Capture learnings** - What would you do differently next time?
5. **Keep it concise** - 2-3 sentences per answer is usually enough

### Workflow Integration

**For feature development:**
1. Commit often with clear messages
2. Reflect after each logical change
3. Review reflections before PRs
4. Include insights in PR descriptions

**For bug fixes:**
1. Document the bug's manifestation
2. Explain root cause analysis
3. Describe the fix and why it works
4. Note preventive measures

## Troubleshooting

### Common Issues

**"Configuration file not found"**
```bash
# Initialize a new config
commit-reflect init

# Or specify config location
commit-reflect --config=/path/to/config.json reflect
```

**"No commit detected"**
```bash
# Specify commit hash explicitly
commit-reflect reflect abc123d

# Check git is properly configured
git log -1
```

**"Storage backend error"**
```bash
# Check file permissions
ls -la .commit-reflections.jsonl

# Verify storage path exists
mkdir -p ~/.commit-reflect

# Check SQLite database
sqlite3 reflections.db ".schema"
```

**"Timeout during session"**
```json
// Increase timeout in config
{
  "session": {
    "timeout_seconds": 600
  }
}
```

### Debug Mode

Enable verbose logging:

```bash
commit-reflect --debug reflect
```

Check logs:

```bash
tail -f ~/.commit-reflect/logs/commit-reflect.log
```

### Getting Help

```bash
# Built-in help
commit-reflect --help
commit-reflect reflect --help

# Check version
commit-reflect --version

# Validate your setup
commit-reflect doctor
```

## What's Next?

- See [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) for development roadmap
- Check [examples/](../examples/) for configuration templates
- Read [ADRs](adr/) for architectural decisions
- Contribute at [GitHub](https://github.com/yourusername/commit-reflect)

## Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/commit-reflect/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/commit-reflect/discussions)
- **Email**: support@commit-reflect.dev
