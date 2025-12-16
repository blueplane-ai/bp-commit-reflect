"""
Shared utilities and types for the Commit Reflection System.

This package contains common types, storage interfaces, and utility functions
used across the CLI, MCP server, and IDE hooks.
"""

__version__ = "0.1.0"

# Re-export key types for convenience
from .types import (
    CommitContext,
    Question,
    QuestionType,
    Reflection,
    ReflectionAnswer,
    StorageBackend,
)

__all__ = [
    "Reflection",
    "ReflectionAnswer",
    "Question",
    "QuestionType",
    "CommitContext",
    "StorageBackend",
]
