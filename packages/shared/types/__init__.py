"""
Core types for the Commit Reflection System.

This module defines the fundamental data structures used throughout
the application.
"""

from .config import (
    Config,
    MCPConfig,
    SessionConfig,
    StorageConfig,
)
from .question import (
    Question,
    QuestionConfig,
    QuestionSet,
    QuestionType,
)
from .reflection import (
    CommitContext,
    Reflection,
    ReflectionAnswer,
    SessionMetadata,
)
from .storage import (
    QueryOptions,
    StorageBackend,
    StorageError,
    StorageResult,
)

__all__ = [
    # Reflection types
    "Reflection",
    "ReflectionAnswer",
    "CommitContext",
    "SessionMetadata",
    # Question types
    "Question",
    "QuestionType",
    "QuestionConfig",
    "QuestionSet",
    # Config types
    "Config",
    "StorageConfig",
    "SessionConfig",
    "MCPConfig",
    # Storage types
    "StorageBackend",
    "StorageResult",
    "QueryOptions",
    "StorageError",
]
