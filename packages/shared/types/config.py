"""
Configuration schema for the Commit Reflection System.

This module defines configuration structures for the entire system including
storage backends, session settings, and MCP server configuration.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from .question import QuestionConfig


class StorageBackendType(str, Enum):
    """Types of storage backends available."""

    JSONL = "jsonl"
    SQLITE = "sqlite"
    GIT = "git"


@dataclass
class StorageConfig:
    """
    Configuration for a storage backend.

    Attributes:
        backend_type: Type of storage backend
        enabled: Whether this backend is enabled
        priority: Priority order (lower = higher priority)
        path: File path for the storage (if applicable)
        options: Backend-specific options
    """

    backend_type: StorageBackendType
    enabled: bool = True
    priority: int = 0
    path: Optional[str] = None
    options: Optional[dict[str, Any]] = None

    def __post_init__(self):
        """Validate and normalize configuration."""
        if isinstance(self.backend_type, str):
            self.backend_type = StorageBackendType(self.backend_type)

        # Set default paths based on backend type
        if self.path is None:
            if self.backend_type == StorageBackendType.JSONL:
                self.path = ".commit-reflections.jsonl"
            elif self.backend_type == StorageBackendType.SQLITE:
                self.path = "~/.commit-reflect/reflections.db"
            elif self.backend_type == StorageBackendType.GIT:
                self.path = ".git"

        if self.options is None:
            self.options = {}

    def to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary for serialization."""
        result = {
            "backend_type": self.backend_type.value,
            "enabled": self.enabled,
            "priority": self.priority,
        }
        if self.path:
            result["path"] = self.path
        if self.options:
            result["options"] = self.options
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StorageConfig":
        """Create config from dictionary representation."""
        return cls(
            backend_type=StorageBackendType(data["backend_type"]),
            enabled=data.get("enabled", True),
            priority=data.get("priority", 0),
            path=data.get("path"),
            options=data.get("options"),
        )

    def get_resolved_path(self) -> Path:
        """Get the resolved absolute path for this storage."""
        if self.path is None:
            raise ValueError("Storage path is not set")
        return Path(self.path).expanduser().resolve()


@dataclass
class SessionConfig:
    """
    Configuration for reflection sessions.

    Attributes:
        timeout: Session timeout in seconds (None = no timeout)
        auto_save: Whether to auto-save progress
        allow_skip: Whether questions can be skipped
        allow_edit: Whether previous answers can be edited
        show_commit_diff: Whether to show commit diff during reflection
        confirm_before_complete: Whether to confirm before completing
    """

    timeout: Optional[int] = None
    auto_save: bool = True
    allow_skip: bool = True
    allow_edit: bool = True
    show_commit_diff: bool = False
    confirm_before_complete: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary for serialization."""
        return {
            "timeout": self.timeout,
            "auto_save": self.auto_save,
            "allow_skip": self.allow_skip,
            "allow_edit": self.allow_edit,
            "show_commit_diff": self.show_commit_diff,
            "confirm_before_complete": self.confirm_before_complete,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionConfig":
        """Create config from dictionary representation."""
        return cls(
            timeout=data.get("timeout"),
            auto_save=data.get("auto_save", True),
            allow_skip=data.get("allow_skip", True),
            allow_edit=data.get("allow_edit", True),
            show_commit_diff=data.get("show_commit_diff", False),
            confirm_before_complete=data.get("confirm_before_complete", True),
        )


@dataclass
class MCPConfig:
    """
    Configuration for the MCP server.

    Attributes:
        enabled: Whether MCP server is enabled
        host: Host to bind to
        port: Port to listen on
        max_concurrent_sessions: Maximum concurrent reflection sessions
        session_cleanup_interval: Interval to clean up stale sessions (seconds)
        process_timeout: Timeout for CLI processes (seconds)
    """

    enabled: bool = False
    host: str = "localhost"
    port: int = 3000
    max_concurrent_sessions: int = 10
    session_cleanup_interval: int = 300
    process_timeout: int = 600

    def to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary for serialization."""
        return {
            "enabled": self.enabled,
            "host": self.host,
            "port": self.port,
            "max_concurrent_sessions": self.max_concurrent_sessions,
            "session_cleanup_interval": self.session_cleanup_interval,
            "process_timeout": self.process_timeout,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MCPConfig":
        """Create config from dictionary representation."""
        return cls(
            enabled=data.get("enabled", False),
            host=data.get("host", "localhost"),
            port=data.get("port", 3000),
            max_concurrent_sessions=data.get("max_concurrent_sessions", 10),
            session_cleanup_interval=data.get("session_cleanup_interval", 300),
            process_timeout=data.get("process_timeout", 600),
        )


@dataclass
class Config:
    """
    Main configuration for the Commit Reflection System.

    This is the root configuration object that encompasses all settings.

    Attributes:
        project_name: Name of the project
        storage_backends: List of storage backend configurations
        session: Session configuration
        questions: Question configuration
        mcp: MCP server configuration
        environment: Environment-specific settings
    """

    project_name: Optional[str] = None
    storage_backends: list[StorageConfig] = field(default_factory=list)
    session: SessionConfig = field(default_factory=SessionConfig)
    questions: Optional[QuestionConfig] = None
    mcp: MCPConfig = field(default_factory=MCPConfig)
    environment: Optional[dict[str, Any]] = None

    def __post_init__(self):
        """Initialize defaults and validate configuration."""
        # If no storage backends configured, use defaults
        if not self.storage_backends:
            self.storage_backends = self._default_storage_backends()

        # Sort storage backends by priority
        self.storage_backends.sort(key=lambda b: b.priority)

        # Ensure session config is initialized
        if self.session is None:
            self.session = SessionConfig()

        # Ensure MCP config is initialized
        if self.mcp is None:
            self.mcp = MCPConfig()

    @staticmethod
    def _default_storage_backends() -> list[StorageConfig]:
        """Get default storage backend configurations."""
        return [
            StorageConfig(
                backend_type=StorageBackendType.JSONL,
                priority=0,
                path=".commit-reflections.jsonl",
            ),
            StorageConfig(
                backend_type=StorageBackendType.SQLITE,
                priority=1,
                path="~/.commit-reflect/reflections.db",
                enabled=False,  # Disabled by default
            ),
        ]

    def to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary for serialization."""
        result = {
            "storage_backends": [b.to_dict() for b in self.storage_backends],
            "session": self.session.to_dict(),
            "mcp": self.mcp.to_dict(),
        }
        if self.project_name:
            result["project_name"] = self.project_name
        if self.questions:
            result["questions"] = self.questions.to_dict()
        if self.environment:
            result["environment"] = self.environment
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Config":
        """Create config from dictionary representation."""
        return cls(
            project_name=data.get("project_name"),
            storage_backends=[StorageConfig.from_dict(b) for b in data.get("storage_backends", [])],
            session=SessionConfig.from_dict(data.get("session", {})),
            questions=QuestionConfig.from_dict(data["questions"]) if "questions" in data else None,
            mcp=MCPConfig.from_dict(data.get("mcp", {})),
            environment=data.get("environment"),
        )

    def get_enabled_storage_backends(self) -> list[StorageConfig]:
        """Get list of enabled storage backends sorted by priority."""
        return [b for b in self.storage_backends if b.enabled]

    def get_storage_backend(self, backend_type: StorageBackendType) -> Optional[StorageConfig]:
        """Get a specific storage backend configuration."""
        for backend in self.storage_backends:
            if backend.backend_type == backend_type:
                return backend
        return None

    def validate(self) -> list[str]:
        """
        Validate the configuration.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Check that at least one storage backend is enabled
        if not self.get_enabled_storage_backends():
            errors.append("At least one storage backend must be enabled")

        # Validate storage paths are writable
        for backend in self.get_enabled_storage_backends():
            try:
                path = backend.get_resolved_path()
                parent = path.parent
                if not parent.exists():
                    errors.append(f"Storage path parent does not exist: {parent}")
            except Exception as e:
                errors.append(f"Invalid storage path for {backend.backend_type}: {e}")

        # Validate MCP config if enabled
        if self.mcp.enabled:
            if self.mcp.port < 1 or self.mcp.port > 65535:
                errors.append(f"Invalid MCP port: {self.mcp.port}")
            if self.mcp.max_concurrent_sessions < 1:
                errors.append("MCP max_concurrent_sessions must be at least 1")

        # Validate session config
        if self.session.timeout is not None and self.session.timeout < 1:
            errors.append("Session timeout must be positive")

        return errors

    @classmethod
    def load_from_file(cls, path: Path) -> "Config":
        """
        Load configuration from a JSON file.

        Args:
            path: Path to the configuration file

        Returns:
            Loaded Config object

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config file is invalid
        """
        import json

        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        try:
            with open(path) as f:
                data = json.load(f)
            return cls.from_dict(data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in config file: {e}") from e
        except Exception as e:
            raise ValueError(f"Error loading config: {e}") from e

    def save_to_file(self, path: Path) -> None:
        """
        Save configuration to a JSON file.

        Args:
            path: Path to save the configuration file
        """
        import json

        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def create_default(cls, project_name: Optional[str] = None) -> "Config":
        """
        Create a default configuration.

        Args:
            project_name: Optional project name

        Returns:
            Config with default settings
        """
        return cls(
            project_name=project_name,
            storage_backends=cls._default_storage_backends(),
            session=SessionConfig(),
            mcp=MCPConfig(),
        )
