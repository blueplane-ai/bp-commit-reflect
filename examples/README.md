# Configuration Examples

This directory contains example configuration files for the Commit Reflection System. Each example demonstrates different use cases and configuration patterns.

## Available Examples

### minimal-config.json
**Use case:** Getting started, simplest possible configuration

- Single JSONL storage backend
- Minimal configuration to get up and running
- Good for testing and experimentation

**Usage:**
```bash
cp examples/minimal-config.json .config/commit-reflect.json
```

### full-config.json
**Use case:** Feature-rich individual setup with custom questions

- Multiple storage backends (JSONL, database, git)
- Custom question set including scale ratings
- Extended session timeout
- UI enhancements (progress indicators, colored output)
- Good for power users who want full control

**Usage:**
```bash
cp examples/full-config.json ~/.commit-reflect/config.json
```

### personal-config.json
**Use case:** Personal, lightweight reflection tracking

- Single JSONL storage for portability
- Minimal questions (summary + learnings)
- Short session timeout for quick captures
- No partial saves - complete or cancel
- Good for solo developers who want quick reflections

**Usage:**
```bash
cp examples/personal-config.json .config/commit-reflect.json
```

### team-config.json
**Use case:** Team-wide standardized reflection process

- Dual storage (SQLite primary + JSONL backup)
- Standardized questions for consistency
- Category selection for change type
- Extended session timeout for detailed reflections
- Allows partial saves for complex changes
- Good for teams with shared reflection database

**Usage:**
```bash
# On shared server or team directory
cp examples/team-config.json /shared/team/.commit-reflect/config.json
```

## Configuration File Locations

The system searches for configuration files in the following order:

1. `./.config/commit-reflect.json` (project-local)
2. `~/.commit-reflect/config.json` (user-global)
3. `/etc/commit-reflect/config.json` (system-wide)

## Customizing Your Configuration

### Storage Backends

**JSONL** - Simple, portable, human-readable
```json
{
  "type": "jsonl",
  "path": "reflections.jsonl"
}
```

**SQLite** - Queryable, efficient for large datasets
```json
{
  "type": "sqlite",
  "path": "reflections.db"
}
```

**Multiple backends:**
```json
{
  "storage": {
    "backends": [
      {"type": "sqlite", "path": "primary.db"},
      {"type": "jsonl", "path": "backup.jsonl"}
    ],
    "primary": "sqlite"
  }
}
```

### Question Types

**Text (single line):**
```json
{
  "id": "summary",
  "text": "Brief summary:",
  "type": "text",
  "required": true
}
```

**Multiline (longer responses):**
```json
{
  "id": "details",
  "text": "Detailed explanation:",
  "type": "multiline",
  "required": false
}
```

**Choice (predefined options):**
```json
{
  "id": "category",
  "text": "Change type:",
  "type": "choice",
  "choices": ["feature", "bugfix", "refactor"],
  "required": true
}
```

### Session Settings

```json
{
  "session": {
    "timeout_seconds": 300,      // 5 minutes
    "allow_partial_save": true   // Save incomplete sessions
  }
}
```

### Git Integration

```json
{
  "git": {
    "auto_detect_commit": true,   // Auto-detect last commit
    "include_diff": false         // Include git diff in context
  }
}
```

## Best Practices

1. **Start simple** - Use `minimal-config.json` initially, then customize
2. **Keep questions focused** - 3-5 questions is ideal
3. **Make critical questions required** - Use `required: false` for optional context
4. **Choose appropriate timeouts** - Balance thoroughness vs. friction
5. **Use multiple backends for important data** - SQLite primary + JSONL backup
6. **Test configurations locally** - Validate before team rollout

## Validation

Validate your configuration:

```bash
commit-reflect validate-config .config/commit-reflect.json
```

## Schema Reference

For complete schema documentation, see `docs/configuration-schema.md`.
