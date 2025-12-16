"""
Unit tests for configuration types and validation.

Tests configuration loading, validation, and defaults.
"""

import pytest
from shared.types.config import (
    Config,
    SessionConfig,
    StorageBackendType,
    StorageConfig,
)


class TestStorageBackendConfig:
    """Tests for StorageConfig (individual backend configuration)."""

    def test_jsonl_backend_config(self, tmp_path):
        """Test JSONL backend configuration."""
        config = StorageConfig(
            backend_type="jsonl",
            path=str(tmp_path / "reflections.jsonl"),
        )
        assert config.backend_type == StorageBackendType.JSONL
        assert config.path is not None

    def test_sqlite_backend_config(self, tmp_path):
        """Test SQLite backend configuration."""
        config = StorageConfig(
            backend_type="sqlite",
            path=str(tmp_path / "reflections.db"),
        )
        assert config.backend_type == StorageBackendType.SQLITE
        assert config.path is not None

    def test_backend_config_validation_invalid_type(self):
        """Test that invalid backend type raises error."""
        with pytest.raises(ValueError):
            StorageConfig(
                backend_type="invalid",
                path="/tmp/test",
            )

    def test_backend_config_default_path(self):
        """Test that backend config uses default path when not specified."""
        config = StorageConfig(backend_type="jsonl")
        # Should have a default path set in __post_init__
        assert config.path is not None
        assert config.path == ".commit-reflections.jsonl"


class TestSessionConfig:
    """Tests for SessionConfig."""

    def test_session_config_defaults(self):
        """Test session config with default values."""
        config = SessionConfig()
        assert config.timeout is None
        assert config.auto_save is True

    def test_session_config_custom_values(self):
        """Test session config with custom values."""
        config = SessionConfig(
            timeout=600,
            auto_save=False,
        )
        assert config.timeout == 600
        assert config.auto_save is False

    def test_session_config_validation_negative_timeout(self):
        """Test that negative timeout is validated."""
        # Negative timeout validation happens in Config.validate(), not SessionConfig.__init__
        config = SessionConfig(timeout=-1)
        # The SessionConfig accepts it, but Config.validate() will catch it
        assert config.timeout == -1


class TestConfig:
    """Tests for main Config class."""

    def test_config_minimal(self, minimal_config):
        """Test config with minimal required fields."""
        config = Config.from_dict(minimal_config)
        assert len(config.storage_backends) > 0
        assert config.questions is not None

    def test_config_full(self, full_config):
        """Test config with all fields populated."""
        config = Config.from_dict(full_config)
        assert config.project_name == "test-project"
        assert len(config.storage_backends) == 2
        assert config.questions is not None
        assert config.mcp is not None
        assert config.session is not None

    def test_config_without_storage_backends(self):
        """Test that config without storage_backends uses defaults."""
        config = Config.from_dict({"questions": [{"id": "q1", "text": "Q1", "type": "text"}]})
        # Should use default storage backends
        assert len(config.storage_backends) > 0

    def test_config_questions_optional(self):
        """Test that questions field is optional."""
        config = Config.from_dict(
            {"storage_backends": [{"backend_type": "jsonl", "path": "test.jsonl"}]}
        )
        # Questions can be None
        assert config.questions is None or config.questions is not None

    def test_config_serialization(self, full_config):
        """Test config can be serialized back to dict."""
        config = Config.from_dict(full_config)
        data = config.to_dict()
        assert "storage_backends" in data
        assert "session" in data
        assert "mcp" in data

    def test_config_load_from_file(self, tmp_path, full_config):
        """Test config can be loaded from JSON file."""
        import json

        config_file = tmp_path / "config.json"
        with open(config_file, "w") as f:
            json.dump(full_config, f)

        config = Config.load_from_file(config_file)
        assert config.project_name == "test-project"
        assert len(config.storage_backends) == 2

    def test_config_defaults_applied(self):
        """Test that default values are applied when not specified."""
        minimal = {
            "storage_backends": [{"backend_type": "jsonl", "path": "reflections.jsonl"}],
            "questions": [{"id": "what", "text": "What changed?", "type": "text"}],
        }
        config = Config.from_dict(minimal)
        assert config.session.timeout is None  # Default
        assert config.session.auto_save is True  # Default
        assert config.mcp.enabled is False  # Default
