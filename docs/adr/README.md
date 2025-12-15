# Architecture Decision Records

This directory contains Architecture Decision Records (ADRs) for the Commit Reflection System.

## What is an ADR?

An Architecture Decision Record (ADR) is a document that captures an important architectural decision made along with its context and consequences.

## Format

Each ADR follows this structure:

- **Title**: Short noun phrase describing the decision
- **Status**: Proposed, Accepted, Deprecated, Superseded
- **Context**: The issue motivating this decision
- **Decision**: The change being proposed or enacted
- **Consequences**: The resulting context after applying the decision

## Index

- [ADR-001: CLI-First Architecture](001-cli-first-architecture.md)
- [ADR-002: Model Context Protocol Integration](002-mcp-integration.md)
- [ADR-003: Multiple Storage Backends](003-multiple-storage-backends.md)
- [ADR-004: Interactive Sequential Question Flow](004-interactive-question-flow.md)
- [ADR-005: REPL Mode with Git Hook Integration](005-repl-mode-git-hook-integration.md)

## Contributing

When making significant architectural decisions, create a new ADR:

1. Copy the template from `000-template.md`
2. Number it sequentially
3. Fill in all sections
4. Submit for review with your PR
5. Update this index
