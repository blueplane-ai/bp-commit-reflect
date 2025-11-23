"""
Core types for the Commit Reflection System.

This module defines the fundamental data structures used throughout
the application.
"""

from .reflection import (
    Reflection,
    ReflectionAnswer,
    CommitContext,
    SessionMetadata,
)
from .question import (
    Question,
    QuestionType,
    QuestionConfig,
    QuestionSet,
)
from .config import (
    Config,
    StorageConfig,
    SessionConfig,
    MCPConfig,
)
from .storage import (
    StorageBackend,
    StorageResult,
    QueryOptions,
    StorageError,
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