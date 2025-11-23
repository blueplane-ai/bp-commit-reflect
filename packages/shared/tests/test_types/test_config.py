"""
Unit tests for configuration types and validation.

Tests configuration loading, validation, and defaults.
"""

import pytest
from shared.types.config import (
    Config,
    StorageConfig,
    StorageBackendConfig,
    SessionConfig,
    GitConfig,
    ConfigValidationError,
)


class TestStorageBackendConfig:
    """Tests for StorageBackendConfig."""

    def test_jsonl_backend_config(self, tmp_path):
        """Test JSONL backend configuration."""
        config = StorageBackendConfig(
            type="jsonl",
            path=str(tmp_path / "reflections.jsonl"),
        )
        assert config.type == "jsonl"
        assert config.path is not None

    def test_sqlite_backend_config(self, tmp_path):
        """Test SQLite backend configuration."""
        config = StorageBackendConfig(
            type="sqlite",
            path=str(tmp_path / "reflections.db"),
        )
        assert config.type == "sqlite"
        assert config.path is not None

    def test_backend_config_validation_invalid_type(self):
        """Test that invalid backend type raises error."""
        with pytest.raises((ValueError, ConfigValidationError)):
            StorageBackendConfig(
                type="invalid",
                path="/tmp/test",
            )

    def test_backend_config_requires_path(self):
        """Test that backend config requires path."""
        with pytest.raises((TypeError, ConfigValidationError)):
            StorageBackendConfig(type="jsonl")


class TestStorageConfig:
    """Tests for StorageConfig."""

    def test_storage_config_single_backend(self, tmp_path):
        """Test storage config with single backend."""
        config = StorageConfig(
            backends=[
                StorageBackendConfig(
                    type="jsonl",
                    path=str(tmp_path / "reflections.jsonl"),
                )
            ]
        )
        assert len(config.backends) == 1
        assert config.backends[0].type == "jsonl"

    def test_storage_config_multiple_backends(self, tmp_path):
        """Test storage config with multiple backends."""
        config = StorageConfig(
            backends=[
                StorageBackendConfig(
                    type="jsonl",
                    path=str(tmp_path / "reflections.jsonl"),
                ),
                StorageBackendConfig(
                    type="sqlite",
                    path=str(tmp_path / "reflections.db"),
                ),
            ],
            primary="jsonl",
        )
        assert len(config.backends) == 2
        assert config.primary == "jsonl"

    def test_storage_config_validation_empty_backends(self):
        """Test that empty backends list raises error."""
        with pytest.raises((ValueError, ConfigValidationError)):
            StorageConfig(backends=[])

    def test_storage_config_validation_invalid_primary(self, tmp_path):
        """Test that primary backend must exist in backends list."""
        with pytest.raises((ValueError, ConfigValidationError)):
            StorageConfig(
                backends=[
                    StorageBackendConfig(
                        type="jsonl",
                        path=str(tmp_path / "reflections.jsonl"),
                    )
                ],
                primary="sqlite",  # Not in backends list
            )


class TestSessionConfig:
    """Tests for SessionConfig."""

    def test_session_config_defaults(self):
        """Test session config with default values."""
        config = SessionConfig()
        assert config.timeout_seconds == 300
        assert config.allow_partial_save is True

    def test_session_config_custom_values(self):
        """Test session config with custom values."""
        config = SessionConfig(
            timeout_seconds=600,
            allow_partial_save=False,
        )
        assert config.timeout_seconds == 600
        assert config.allow_partial_save is False

    def test_session_config_validation_negative_timeout(self):
        """Test that negative timeout raises error."""
        with pytest.raises((ValueError, ConfigValidationError)):
            SessionConfig(timeout_seconds=-1)


class TestGitConfig:
    """Tests for GitConfig."""

    def test_git_config_defaults(self):
        """Test git config with default values."""
        config = GitConfig()
        assert config.auto_detect_commit is True
        assert config.include_diff is False

    def test_git_config_custom_values(self):
        """Test git config with custom values."""
        config = GitConfig(
            auto_detect_commit=False,
            include_diff=True,
        )
        assert config.auto_detect_commit is False
        assert config.include_diff is True


class TestConfig:
    """Tests for main Config class."""

    def test_config_minimal(self, minimal_config):
        """Test config with minimal required fields."""
        config = Config.from_dict(minimal_config)
        assert config.version == "1.0"
        assert len(config.storage.backends) > 0
        assert len(config.questions) > 0

    def test_config_full(self, full_config):
        """Test config with all fields populated."""
        config = Config.from_dict(full_config)
        assert config.version == "1.0"
        assert len(config.storage.backends) == 2
        assert len(config.questions) == 5
        assert config.git is not None
        assert config.session is not None

    def test_config_validation_missing_version(self, minimal_config):
        """Test that missing version raises error."""
        del minimal_config["version"]
        with pytest.raises((KeyError, ConfigValidationError)):
            Config.from_dict(minimal_config)

    def test_config_validation_missing_storage(self, minimal_config):
        """Test that missing storage raises error."""
        del minimal_config["storage"]
        with pytest.raises((KeyError, ConfigValidationError)):
            Config.from_dict(minimal_config)

    def test_config_validation_missing_questions(self, minimal_config):
        """Test that missing questions raises error."""
        del minimal_config["questions"]
        with pytest.raises((KeyError, ConfigValidationError)):
            Config.from_dict(minimal_config)

    def test_config_serialization(self, full_config):
        """Test config can be serialized back to dict."""
        config = Config.from_dict(full_config)
        data = config.to_dict()
        assert data["version"] == "1.0"
        assert "storage" in data
        assert "questions" in data

    def test_config_load_from_file(self, tmp_path, full_config):
        """Test config can be loaded from JSON file."""
        import json

        config_file = tmp_path / "config.json"
        with open(config_file, "w") as f:
            json.dump(full_config, f)

        config = Config.from_file(config_file)
        assert config.version == "1.0"
        assert len(config.questions) == 5

    def test_config_defaults_applied(self):
        """Test that default values are applied when not specified."""
        minimal = {
            "version": "1.0",
            "storage": {
                "backends": [{"type": "jsonl", "path": "reflections.jsonl"}]
            },
            "questions": [
                {"id": "what", "text": "What changed?", "type": "text"}
            ],
        }
        config = Config.from_dict(minimal)
        assert config.session.timeout_seconds == 300  # Default
        assert config.git.auto_detect_commit is True  # Default
