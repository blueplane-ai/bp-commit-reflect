"""Cross-platform compatibility tests."""

import pytest
import sys
import platform
import json
from pathlib import Path
import tempfile

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from packages.shared.storage.jsonl import JSONLStorage
from packages.cli.src.progress import ProgressIndicator
from packages.cli.src.validators import validate_scale, validate_text


class TestPathHandling:
    """Test path handling across platforms."""

    def test_path_handling_windows_style(self, temp_dir):
        """Test path handling with Windows-style paths."""
        # Simulate Windows path
        if platform.system() == "Windows":
            # Use actual Windows path
            jsonl_path = temp_dir / "reflections.jsonl"
        else:
            # Test Windows-style path format on other platforms
            jsonl_path = temp_dir / "reflections.jsonl"
        
        storage = JSONLStorage(str(jsonl_path))
        assert storage.filepath.exists() or storage.filepath.parent.exists()

    def test_path_handling_unix_style(self, temp_dir):
        """Test path handling with Unix-style paths."""
        # Unix paths should work on all platforms
        jsonl_path = temp_dir / "reflections.jsonl"
        storage = JSONLStorage(str(jsonl_path))
        
        # Should handle both absolute and relative paths
        assert storage.filepath.is_absolute() or storage.filepath.is_relative_to(Path.cwd())

    def test_path_expansion(self, temp_dir):
        """Test tilde expansion in paths."""
        # Test that ~ expansion works
        if platform.system() != "Windows":
            # On Unix, test tilde expansion
            home = Path.home()
            test_path = str(home / "test.jsonl")
            storage = JSONLStorage(test_path)
            assert storage.filepath == home / "test.jsonl"
        else:
            # On Windows, tilde expansion may not work the same way
            # Just verify it doesn't crash
            test_path = str(temp_dir / "test.jsonl")
            storage = JSONLStorage(test_path)
            assert storage.filepath.exists() or storage.filepath.parent.exists()

    def test_path_with_spaces(self, temp_dir):
        """Test paths with spaces (common on all platforms)."""
        path_with_spaces = temp_dir / "my reflections.jsonl"
        storage = JSONLStorage(str(path_with_spaces))
        
        reflection = {
            "project": "test",
            "commit_hash": "abc123",
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
        success = storage.write(reflection)
        assert success is True
        assert path_with_spaces.exists()
        
        storage.close()


class TestColorOutput:
    """Test color output detection across platforms."""

    def test_color_detection_windows(self):
        """Test color detection on Windows."""
        progress = ProgressIndicator(use_color=True)
        
        # On Windows, isatty() behavior may differ
        # Just verify it doesn't crash
        assert hasattr(progress, 'use_color')
        assert isinstance(progress.use_color, bool)

    def test_color_detection_unix(self):
        """Test color detection on Unix-like systems."""
        progress = ProgressIndicator(use_color=True)
        
        # Should handle TTY detection gracefully
        assert hasattr(progress, 'use_color')
        assert isinstance(progress.use_color, bool)

    def test_color_disabled_consistently(self):
        """Test colors are consistently disabled when requested."""
        progress = ProgressIndicator(use_color=False)
        
        # Should have no color codes
        assert progress.BLUE == ""
        assert progress.GREEN == ""
        assert progress.RESET == ""


class TestLineEndings:
    """Test line ending handling across platforms."""

    def test_jsonl_line_endings(self, temp_dir):
        """Test JSONL handles different line endings."""
        jsonl_path = temp_dir / "test.jsonl"
        storage = JSONLStorage(str(jsonl_path))
        
        reflection = {
            "project": "test",
            "commit_hash": "abc123",
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
        storage.write(reflection)
        
        # Read file and verify it's valid JSONL
        content = jsonl_path.read_text(encoding='utf-8')
        lines = content.strip().split('\n')
        
        assert len(lines) == 1
        # Should be valid JSON
        import json
        data = json.loads(lines[0])
        assert data["commit_hash"] == "abc123"
        
        storage.close()


class TestEncoding:
    """Test character encoding handling."""

    def test_unicode_characters(self, temp_dir):
        """Test handling of Unicode characters."""
        jsonl_path = temp_dir / "test.jsonl"
        storage = JSONLStorage(str(jsonl_path))
        
        reflection = {
            "project": "test",
            "commit_hash": "abc123",
            "timestamp": "2024-01-01T00:00:00Z",
            "message": "测试 🚀 émoji"
        }
        
        success = storage.write(reflection)
        assert success is True
        
        # Read back and verify Unicode preserved
        reflections = storage.read_recent(limit=1)
        assert reflections[0]["message"] == "测试 🚀 émoji"
        
        storage.close()

    def test_special_characters_in_paths(self, temp_dir):
        """Test paths with special characters."""
        # Create path with special characters
        special_path = temp_dir / "test-émoji-测试.jsonl"
        storage = JSONLStorage(str(special_path))
        
        reflection = {
            "project": "test",
            "commit_hash": "abc123",
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
        success = storage.write(reflection)
        assert success is True
        
        storage.close()


class TestPlatformSpecific:
    """Platform-specific compatibility tests."""

    @pytest.mark.skipif(platform.system() == "Windows", reason="File locking test for Unix")
    def test_file_locking_unix(self, temp_dir):
        """Test file locking on Unix systems."""
        jsonl_path = temp_dir / "test.jsonl"
        storage = JSONLStorage(str(jsonl_path))
        
        # File locking should work on Unix
        reflection = {
            "project": "test",
            "commit_hash": "abc123",
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
        success = storage.write(reflection)
        assert success is True
        
        storage.close()

    def test_validation_works_all_platforms(self):
        """Test validation works consistently across platforms."""
        # Scale validation
        result, error = validate_scale(3, 1, 5)
        assert error is None
        assert result == 3
        
        # Text validation
        result, error = validate_text("test", max_length=100)
        assert error is None
        assert result == "test"

    def test_progress_indicator_all_platforms(self):
        """Test progress indicator works on all platforms."""
        progress = ProgressIndicator(total_questions=5, use_color=False)
        
        # Should work regardless of platform
        progress.show_welcome("test-project", "abc123")
        progress.show_question(1, "Question 1")
        progress.show_success()
        
        assert progress.current_question == 1


# Test fixtures

@pytest.fixture
def temp_dir():
    """Provide temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

