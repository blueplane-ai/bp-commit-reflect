# Quick Start Guide

Get up and running with Commit Reflection in 5 minutes.

## Step 1: Install

```bash
pip install commit-reflect
```

## Step 2: Initialize

In your git repository:

```bash
cd your-project
commit-reflect init
```

This creates `.config/commit-reflect.json` with default settings.

## Step 3: Make a commit

```bash
git add .
git commit -m "Your commit message"
```

## Step 4: Reflect

```bash
commit-reflect reflect
```

Answer the guided questions about your commit:

```
❓ What changed in this commit?
> [Your answer]

❓ Why was this change necessary?
> [Your answer]

❓ How was this implemented?
> [Your answer]
```

## Step 5: View your reflections

```bash
# List all reflections
commit-reflect list

# Show details
commit-reflect show <commit-hash>

# Export to JSON
commit-reflect export --format json > reflections.json
```

## That's it!

You're now capturing valuable context with every commit.

### Next Steps

- **Customize questions**: Edit `.config/commit-reflect.json`
- **Integrate with your IDE**: See [USER_GUIDE.md#ide-integration](USER_GUIDE.md#ide-integration)
- **Explore storage options**: Check [examples/](../examples/) for different configurations
- **Automate reflections**: Set up git hooks or IDE triggers

### Example Configuration

Want to start simple? Use this minimal config:

```json
{
  "version": "1.0",
  "storage": {
    "backends": [
      {"type": "jsonl", "path": ".commit-reflections.jsonl"}
    ]
  },
  "questions": [
    {"id": "what", "text": "What changed?", "type": "text", "required": true},
    {"id": "why", "text": "Why?", "type": "text", "required": true}
  ]
}
```

### Helpful Commands

```bash
# Validate your config
commit-reflect validate-config

# Get help
commit-reflect --help

# Check system status
commit-reflect doctor
```

For more details, see the [User Guide](USER_GUIDE.md).
