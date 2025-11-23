"""
Unit tests for reflection types and validation.

Tests the core Reflection data model including:
- Data validation and type checking
- Serialization and deserialization
- Field requirements and constraints
"""

import pytest
from datetime import datetime, timezone
from types.reflection import Reflection, CommitMetadata, ReflectionValidationError


class TestCommitMetadata:
    """Tests for CommitMetadata data class."""

    def test_commit_metadata_creation(self, mock_commit_metadata):
        """Test basic commit metadata creation."""
        metadata = CommitMetadata(**mock_commit_metadata)
        assert metadata.hash == "abc123def456"
        assert metadata.author == "Test Author <test@example.com>"
        assert metadata.branch == "feature/auth"

    def test_commit_metadata_with_minimal_fields(self):
        """Test commit metadata with only required fields."""
        metadata = CommitMetadata(
            hash="abc123",
            author="Test <test@example.com>",
            timestamp="2024-01-15T10:30:00Z",
            message="test commit",
        )
        assert metadata.hash == "abc123"
        assert metadata.files_changed is None
        assert metadata.insertions is None

    def test_commit_metadata_validation_missing_hash(self):
        """Test that missing hash raises validation error."""
        with pytest.raises((TypeError, ReflectionValidationError)):
            CommitMetadata(
                author="Test <test@example.com>",
                timestamp="2024-01-15T10:30:00Z",
                message="test commit",
            )


class TestReflection:
    """Tests for Reflection data class."""

    def test_reflection_creation(self, sample_reflection):
        """Test creating a complete reflection."""
        reflection = Reflection(**sample_reflection)
        assert reflection.commit_hash == "abc123def456"
        assert reflection.what_changed is not None
        assert reflection.why_changed is not None

    def test_reflection_with_minimal_fields(self):
        """Test reflection with only required fields."""
        reflection = Reflection(
            commit_hash="abc123",
            timestamp=datetime.now(timezone.utc).isoformat(),
            what_changed="Added feature",
            why_changed="User request",
        )
        assert reflection.commit_hash == "abc123"
        assert reflection.how_changed is None
        assert reflection.challenges is None

    def test_reflection_serialization(self, sample_reflection):
        """Test reflection can be serialized to dict."""
        reflection = Reflection(**sample_reflection)
        data = reflection.to_dict()
        assert isinstance(data, dict)
        assert data["commit_hash"] == sample_reflection["commit_hash"]
        assert data["what_changed"] == sample_reflection["what_changed"]

    def test_reflection_deserialization(self, sample_reflection):
        """Test reflection can be created from dict."""
        reflection = Reflection.from_dict(sample_reflection)
        assert reflection.commit_hash == sample_reflection["commit_hash"]
        assert reflection.what_changed == sample_reflection["what_changed"]

    def test_reflection_timestamp_validation(self):
        """Test that invalid timestamp format raises error."""
        with pytest.raises((ValueError, ReflectionValidationError)):
            Reflection(
                commit_hash="abc123",
                timestamp="invalid-timestamp",
                what_changed="test",
                why_changed="test",
            )

    def test_reflection_with_empty_strings(self):
        """Test that empty strings in required fields raise validation error."""
        with pytest.raises((ValueError, ReflectionValidationError)):
            Reflection(
                commit_hash="abc123",
                timestamp=datetime.now(timezone.utc).isoformat(),
                what_changed="",  # Empty string should fail
                why_changed="test",
            )

    def test_reflection_equality(self, sample_reflection):
        """Test two reflections with same data are equal."""
        ref1 = Reflection(**sample_reflection)
        ref2 = Reflection(**sample_reflection)
        assert ref1 == ref2

    def test_reflection_with_commit_metadata(self, sample_reflection):
        """Test reflection with embedded commit metadata."""
        reflection = Reflection(**sample_reflection)
        assert reflection.commit_metadata is not None
        assert reflection.commit_metadata["hash"] == "abc123def456"


class TestReflectionValidation:
    """Tests for reflection validation rules."""

    def test_validate_required_fields(self):
        """Test that all required fields must be present."""
        # Missing what_changed
        with pytest.raises((TypeError, ReflectionValidationError)):
            Reflection(
                commit_hash="abc123",
                timestamp=datetime.now(timezone.utc).isoformat(),
                why_changed="test",
            )

    def test_validate_commit_hash_format(self):
        """Test commit hash format validation."""
        # Hash too short
        with pytest.raises((ValueError, ReflectionValidationError)):
            Reflection(
                commit_hash="abc",  # Too short
                timestamp=datetime.now(timezone.utc).isoformat(),
                what_changed="test",
                why_changed="test",
            )

    def test_validate_optional_fields_can_be_none(self, sample_reflection):
        """Test that optional fields can be None."""
        del sample_reflection["challenges"]
        del sample_reflection["learnings"]
        reflection = Reflection(**sample_reflection)
        assert reflection.challenges is None
        assert reflection.learnings is None

    def test_validate_timestamp_is_iso_format(self):
        """Test timestamp must be in ISO format."""
        valid_timestamp = datetime.now(timezone.utc).isoformat()
        reflection = Reflection(
            commit_hash="abc123def456",
            timestamp=valid_timestamp,
            what_changed="test",
            why_changed="test",
        )
        assert reflection.timestamp == valid_timestamp
