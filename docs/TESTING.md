# Testing Guide

This document describes how to run and write tests for the Commit Reflection System.

## Table of Contents

- [Running Tests](#running-tests)
- [Test Organization](#test-organization)
- [Writing Tests](#writing-tests)
- [Test Fixtures](#test-fixtures)
- [Coverage](#coverage)
- [Continuous Integration](#continuous-integration)

## Running Tests

### Run all tests

```bash
# From repository root
pytest

# From shared package
cd packages/shared
pytest
```

### Run specific test categories

```bash
# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# Storage tests
pytest -m storage

# Type tests
pytest -m types
```

### Run specific test files

```bash
# Single test file
pytest packages/shared/tests/types/test_reflection.py

# Multiple test files
pytest packages/shared/tests/types/ packages/shared/tests/storage/
```

### Run specific test functions

```bash
# Single test function
pytest packages/shared/tests/types/test_reflection.py::TestReflection::test_reflection_creation

# Pattern matching
pytest -k "test_reflection"
pytest -k "validation"
```

### Run with coverage

```bash
# Generate coverage report
pytest --cov=packages/shared --cov-report=html

# View coverage in browser
open htmlcov/index.html

# Terminal coverage report
pytest --cov=packages/shared --cov-report=term-missing
```

### Run with verbose output

```bash
# Verbose mode
pytest -v

# Very verbose with output
pytest -vv -s

# Show local variables on failure
pytest -l
```

## Test Organization

### Directory Structure

```
packages/shared/tests/
├── conftest.py              # Shared fixtures
├── types/                   # Type definition tests
│   ├── test_reflection.py
│   ├── test_question.py
│   ├── test_config.py
│   └── test_storage.py
├── storage/                 # Storage backend tests
│   ├── test_jsonl_backend.py
│   ├── test_sqlite_backend.py
│   └── test_storage_factory.py
├── utils/                   # Utility function tests
│   └── test_validators.py
└── integration/             # Integration tests
    ├── test_session_lifecycle.py
    ├── test_mcp_communication.py
    └── test_multi_backend.py
```

### Test Markers

Tests are categorized using pytest markers:

```python
@pytest.mark.unit          # Unit tests for individual components
@pytest.mark.integration   # Integration tests
@pytest.mark.slow          # Tests that take significant time
@pytest.mark.storage       # Storage backend tests
@pytest.mark.types         # Type definition tests
@pytest.mark.mcp           # MCP server tests
@pytest.mark.cli           # CLI interface tests
```

List all markers:

```bash
pytest --markers
```

## Writing Tests

### Test Structure

Follow the Arrange-Act-Assert pattern:

```python
def test_reflection_creation(sample_reflection):
    # Arrange
    data = sample_reflection

    # Act
    reflection = Reflection(**data)

    # Assert
    assert reflection.commit_hash == data["commit_hash"]
    assert reflection.what_changed == data["what_changed"]
```

### Using Fixtures

```python
def test_with_fixtures(
    mock_commit_metadata,
    temp_jsonl_file,
    sample_reflection
):
    # Use fixtures directly as function parameters
    assert mock_commit_metadata["hash"] is not None
    assert temp_jsonl_file.exists()
    assert sample_reflection["commit_hash"] is not None
```

### Parametrized Tests

Test multiple scenarios:

```python
@pytest.mark.parametrize("commit_hash,expected", [
    ("abc123def456", True),
    ("short", False),
    ("", False),
])
def test_commit_hash_validation(commit_hash, expected):
    if expected:
        reflection = Reflection(
            commit_hash=commit_hash,
            timestamp="2024-01-01T00:00:00Z",
            what_changed="test",
            why_changed="test"
        )
        assert reflection.commit_hash == commit_hash
    else:
        with pytest.raises(ValidationError):
            Reflection(commit_hash=commit_hash, ...)
```

### Testing Exceptions

```python
def test_validation_error():
    with pytest.raises(ReflectionValidationError) as exc_info:
        Reflection(commit_hash="", ...)

    assert "commit_hash" in str(exc_info.value)
```

### Using Mocks

```python
def test_storage_backend_write(mocker):
    # Create mock
    mock_backend = mocker.Mock()
    mock_backend.write.return_value = True

    # Test
    result = mock_backend.write({"data": "test"})

    # Verify
    assert result is True
    mock_backend.write.assert_called_once()
```

### Async Tests

```python
@pytest.mark.asyncio
async def test_async_operation():
    result = await some_async_function()
    assert result is not None
```

## Test Fixtures

### Available Fixtures

See `packages/shared/tests/conftest.py` for all available fixtures:

#### Mock Data Fixtures

- `mock_commit_metadata` - Basic commit metadata
- `mock_commit_with_stats` - Commit with detailed statistics
- `mock_large_commit` - Large refactoring commit
- `sample_reflection` - Complete reflection data
- `partial_reflection` - Partial reflection data

#### Storage Fixtures

- `temp_jsonl_file` - Temporary JSONL file
- `temp_sqlite_db` - Temporary SQLite database
- `jsonl_with_sample_data` - Pre-populated JSONL file
- `mock_storage_backend` - Mock storage backend

#### Configuration Fixtures

- `minimal_config` - Minimal valid configuration
- `full_config` - Full configuration with all options

#### Generator Fixtures

- `generate_reflections` - Generate N test reflections
- `generate_commit_metadata` - Generate N commit metadata objects

### Creating Custom Fixtures

Add to `conftest.py` or test files:

```python
@pytest.fixture
def custom_config():
    return {
        "version": "1.0",
        "storage": {...},
        "questions": [...]
    }

@pytest.fixture
def setup_test_environment(tmp_path):
    # Setup
    test_dir = tmp_path / "test_env"
    test_dir.mkdir()

    yield test_dir

    # Teardown
    # (cleanup happens automatically with tmp_path)
```

## Coverage

### Coverage Requirements

- **Minimum target**: 80% code coverage
- **Goal**: 90%+ coverage for core components
- **Required**: 100% coverage for critical paths (data validation, storage operations)

### Check Coverage

```bash
# Generate coverage report
pytest --cov=packages/shared --cov-report=term-missing

# HTML report for detailed analysis
pytest --cov=packages/shared --cov-report=html
open htmlcov/index.html

# XML report for CI
pytest --cov=packages/shared --cov-report=xml
```

### Coverage Configuration

See `pytest.ini` and `packages/shared/pyproject.toml` for coverage settings.

Excluded from coverage:
- Test files themselves
- `__init__.py` files
- Abstract methods
- Debug code
- Type checking blocks

## Continuous Integration

### GitHub Actions

Tests run automatically on:
- Pull requests
- Pushes to main/develop
- Nightly builds

### CI Configuration

See `.github/workflows/test.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.9, 3.10, 3.11, 3.12]

    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install dependencies
        run: |
          pip install -e packages/shared[dev]
      - name: Run tests
        run: |
          pytest --cov --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

### Local CI Simulation

Run the same checks as CI locally:

```bash
# Run all checks
./scripts/ci-checks.sh

# Individual checks
pytest --cov --cov-report=xml
mypy packages/shared
black --check packages/shared
ruff packages/shared
```

## Best Practices

1. **Write tests first** - TDD helps design better APIs
2. **Test behavior, not implementation** - Tests should verify what code does, not how
3. **Keep tests focused** - One concept per test
4. **Use descriptive names** - `test_reflection_validates_required_fields` not `test_1`
5. **Avoid test interdependence** - Tests should run independently
6. **Mock external dependencies** - Don't rely on network, file system, etc.
7. **Test edge cases** - Empty strings, None values, boundary conditions
8. **Maintain test fixtures** - Keep conftest.py organized and documented

## Debugging Tests

### Run with debugger

```bash
# Drop into pdb on failure
pytest --pdb

# Drop into pdb at start of test
pytest --trace
```

### Show print statements

```bash
# Show all output
pytest -s

# Show only for failed tests
pytest --tb=short
```

### Verbose failure output

```bash
# Show local variables
pytest -l

# Very verbose
pytest -vv

# Full stack traces
pytest --tb=long
```

## Further Reading

- [pytest documentation](https://docs.pytest.org/)
- [pytest-cov documentation](https://pytest-cov.readthedocs.io/)
- [Testing Best Practices](https://docs.python-guide.org/writing/tests/)
