# Commit Reflection Shared Package

This package contains shared types, interfaces, and utilities used across all components of the Commit Reflection System (CLI, MCP Server, and IDE Hooks).

## Package Structure

```
shared/
├── types/              # Core type definitions
│   ├── reflection.py   # Reflection data models
│   ├── question.py     # Question and answer types
│   ├── config.py       # Configuration schema
│   └── storage.py      # Storage backend interfaces
├── storage/            # Storage implementations (future)
├── utils/              # Utility functions (future)
└── tests/              # Tests for shared code
```

## Core Types

### Reflection Types ([reflection.py](types/reflection.py))

The reflection module defines the core data structures for storing commit reflections:

#### `Reflection`
The primary data structure representing a complete commit reflection.

**Key Attributes:**
- `id`: Unique identifier (UUID)
- `answers`: List of reflection answers
- `commit_context`: Information about the commit
- `session_metadata`: Information about the reflection session
- `created_at`, `updated_at`: Timestamps

**Methods:**
- `to_dict()`: Serialize to dictionary
- `from_dict(data)`: Deserialize from dictionary
- `get_answer_by_question_id(question_id)`: Retrieve specific answer
- `is_complete(expected_count)`: Check if all questions answered
- `summary()`: Generate brief summary

#### `ReflectionAnswer`
A single answer to a reflection question.

**Key Attributes:**
- `question_id`: ID of the question
- `question_text`: Full text of the question
- `answer`: User's response
- `answered_at`: Timestamp
- `metadata`: Optional metadata

#### `CommitContext`
Context information about the commit being reflected upon.

**Key Attributes:**
- `commit_hash`: Git commit hash
- `commit_message`: Original commit message
- `branch`: Branch name
- `author_name`, `author_email`: Author information
- `timestamp`: Commit timestamp
- `files_changed`, `insertions`, `deletions`: Change statistics
- `changed_files`: List of modified file paths

#### `SessionMetadata`
Metadata about the reflection session itself.

**Key Attributes:**
- `session_id`: Unique session identifier (UUID)
- `started_at`, `completed_at`: Session timestamps
- `project_name`: Project being reflected upon
- `tool_version`: Version of reflection tool
- `environment`: Environment info (IDE, terminal, MCP)
- `interrupted`: Whether session was interrupted
- `additional_context`: Any additional context

---

### Question Types ([question.py](types/question.py))

The question module defines how reflection questions are structured and validated:

#### `QuestionType` (Enum)
Types of questions available:
- `TEXT`: Free-form text response
- `MULTILINE`: Multi-line text response
- `RATING`: Numeric rating (e.g., 1-5)
- `CHOICE`: Single choice from options
- `MULTICHOICE`: Multiple choices from options
- `BOOLEAN`: Yes/No question
- `SCALE`: Scaled response (e.g., 1-10)

#### `Question`
A single reflection question with configuration.

**Key Attributes:**
- `id`: Unique question identifier
- `text`: Question text to display
- `question_type`: Type of question (QuestionType)
- `required`: Whether answer is required
- `help_text`: Optional help text
- `placeholder`: Optional placeholder
- `validation_rules`: Optional validation rules
- `options`: For choice questions, available options
- `min_value`, `max_value`: For rating/scale questions
- `order`: Display order
- `conditional`: Optional function to determine if question should be shown

**Methods:**
- `validate_answer(answer)`: Validate an answer
- `should_ask(context)`: Check if question should be asked based on context

#### `QuestionSet`
A complete set of questions for a reflection session.

**Key Attributes:**
- `name`: Name of the question set
- `questions`: List of questions
- `description`: Optional description
- `version`: Version of question set

**Methods:**
- `get_question_by_id(id)`: Retrieve specific question
- `get_questions_for_context(context)`: Get questions based on conditional logic
- `validate_all_answers(answers)`: Validate all answers

#### `create_default_question_set()`
Factory function that returns the default 5 questions:
1. What did you do in this commit?
2. Synergy rating (1-5 scale)
3. Blockers encountered
4. Learnings
5. Next steps

---

### Configuration Types ([config.py](types/config.py))

The config module defines configuration structures for the entire system:

#### `StorageBackendType` (Enum)
Available storage backends:
- `JSONL`: JSON Lines format
- `SQLITE`: SQLite database
- `GIT`: Git commit message storage

#### `StorageConfig`
Configuration for a storage backend.

**Key Attributes:**
- `backend_type`: Type of backend (StorageBackendType)
- `enabled`: Whether backend is enabled
- `priority`: Priority order (lower = higher priority)
- `path`: File path for storage
- `options`: Backend-specific options

**Methods:**
- `get_resolved_path()`: Get absolute path for storage

#### `SessionConfig`
Configuration for reflection sessions.

**Key Attributes:**
- `timeout`: Session timeout in seconds
- `auto_save`: Whether to auto-save progress
- `allow_skip`: Whether questions can be skipped
- `allow_edit`: Whether previous answers can be edited
- `show_commit_diff`: Whether to show diff during reflection
- `confirm_before_complete`: Require confirmation before completing

#### `MCPConfig`
Configuration for the MCP server.

**Key Attributes:**
- `enabled`: Whether MCP server is enabled
- `host`, `port`: Server binding
- `max_concurrent_sessions`: Maximum concurrent sessions
- `session_cleanup_interval`: Cleanup interval
- `process_timeout`: Timeout for CLI processes

#### `Config`
Main configuration object that encompasses all settings.

**Key Attributes:**
- `project_name`: Name of project
- `storage_backends`: List of storage configurations
- `session`: Session configuration
- `questions`: Question configuration
- `mcp`: MCP server configuration
- `environment`: Environment-specific settings

**Methods:**
- `validate()`: Validate configuration
- `get_enabled_storage_backends()`: Get enabled backends
- `load_from_file(path)`: Load from JSON file
- `save_to_file(path)`: Save to JSON file
- `create_default(project_name)`: Create default configuration

---

### Storage Types ([storage.py](types/storage.py))

The storage module defines abstract interfaces for storage backends:

#### `StorageBackend` (Abstract Base Class)
Abstract interface that all storage implementations must implement.

**Abstract Methods:**
- `initialize()`: Initialize the storage backend
- `close()`: Close and clean up resources
- `save_reflection(reflection)`: Save a reflection
- `get_reflection(reflection_id)`: Retrieve a reflection by ID
- `query_reflections(options)`: Query reflections with filters
- `delete_reflection(reflection_id)`: Delete a reflection
- `count_reflections(filter_by)`: Count reflections
- `health_check()`: Check backend health

**Concrete Helper Methods:**
- `is_initialized()`: Check if initialized
- `validate_reflection(reflection)`: Validate before saving
- `get_recent_reflections(limit, project)`: Get recent reflections
- `get_reflections_by_commit(hash)`: Get reflections for commit
- `get_reflections_by_date_range(from, to)`: Get reflections in date range

#### `QueryOptions`
Options for querying reflections.

**Key Attributes:**
- `limit`: Maximum results
- `offset`: Number to skip
- `sort_by`: Field to sort by
- `sort_order`: ASC or DESC
- `filter_by`: Field filters
- `date_from`, `date_to`: Date range filters
- `project_name`, `branch`, `author_email`: Specific filters

#### `StorageResult`
Result of a storage operation.

**Key Attributes:**
- `success`: Whether operation succeeded
- `message`: Optional message
- `data`: Optional returned data
- `error`: Optional error

**Factory Methods:**
- `success_result(message, data)`: Create success result
- `error_result(message, error)`: Create error result

#### `MultiBackendStorage`
Coordinator for multiple storage backends with priority and fallback logic.

**Methods:**
- `initialize_all()`: Initialize all backends
- `save_to_all(reflection)`: Save to all backends
- `get_reflection(id)`: Get from first available backend
- `close_all()`: Close all backends

#### Storage Exceptions
- `StorageError`: Base exception
- `StorageConnectionError`: Connection errors
- `StorageWriteError`: Write errors
- `StorageReadError`: Read errors
- `StorageValidationError`: Validation errors

---

## Type Contracts

### Serialization Contract

All core types implement consistent serialization:

```python
# To dictionary (for JSON, storage, etc.)
data_dict = instance.to_dict()

# From dictionary
instance = ClassName.from_dict(data_dict)
```

**Guarantees:**
- All timestamps serialized as ISO 8601 strings
- All UUIDs serialized as strings
- Nested objects recursively serialized
- Optional fields only included if not None
- Deserialization validates types and required fields

### Validation Contract

Types that require validation implement:

```python
is_valid, error_message = instance.validate(...)
```

**Returns:**
- Tuple of `(bool, Optional[str])`
- First element is `True` if valid, `False` if invalid
- Second element is error message if invalid, `None` if valid

### Immutability Guidelines

- **Immutable:** Question definitions (id, text, type)
- **Mutable:** Configuration settings, session state
- **Append-only:** Reflection answers (can add, not modify)

---

## Usage Examples

### Creating a Reflection

```python
from datetime import datetime
from uuid import uuid4
from shared.types import (
    Reflection,
    ReflectionAnswer,
    CommitContext,
    SessionMetadata,
)

# Create commit context
commit_ctx = CommitContext(
    commit_hash="abc123def456",
    commit_message="Add user authentication",
    branch="feature/auth",
    author_name="Jane Doe",
    author_email="jane@example.com",
    timestamp=datetime.now(),
    files_changed=5,
    insertions=120,
    deletions=30,
    changed_files=["auth.py", "models.py"],
)

# Create session metadata
session_meta = SessionMetadata(
    session_id=uuid4(),
    started_at=datetime.now(),
    completed_at=datetime.now(),
    project_name="my-app",
    tool_version="1.0.0",
    environment="cli",
)

# Create answers
answers = [
    ReflectionAnswer(
        question_id="what_did_you_do",
        question_text="What did you do in this commit?",
        answer="Implemented JWT-based authentication",
        answered_at=datetime.now(),
    ),
    ReflectionAnswer(
        question_id="synergy_rating",
        question_text="Rate alignment with project goals (1-5)",
        answer="4",
        answered_at=datetime.now(),
    ),
]

# Create reflection
reflection = Reflection(
    id=uuid4(),
    answers=answers,
    commit_context=commit_ctx,
    session_metadata=session_meta,
    created_at=datetime.now(),
    updated_at=datetime.now(),
)

# Serialize
data = reflection.to_dict()
```

### Working with Questions

```python
from shared.types import Question, QuestionType, QuestionSet

# Create a custom question
question = Question(
    id="custom_q1",
    text="How confident are you in this code?",
    question_type=QuestionType.RATING,
    required=True,
    min_value=1,
    max_value=5,
    help_text="1 = Not confident, 5 = Very confident",
    order=1,
)

# Validate an answer
is_valid, error = question.validate_answer(4)
if is_valid:
    print("Answer is valid")
else:
    print(f"Invalid: {error}")

# Create question set
question_set = QuestionSet(
    name="confidence-check",
    questions=[question],
    version="1.0",
)
```

### Loading Configuration

```python
from pathlib import Path
from shared.types import Config

# Load from file
config = Config.load_from_file(Path(".commit-reflect.json"))

# Validate
errors = config.validate()
if errors:
    print("Configuration errors:", errors)

# Get enabled backends
backends = config.get_enabled_storage_backends()
for backend in backends:
    print(f"Using {backend.backend_type} at {backend.path}")
```

### Implementing a Storage Backend

```python
from shared.types import StorageBackend, StorageResult, QueryOptions, Reflection
from typing import List, Optional
from uuid import UUID

class MyStorageBackend(StorageBackend):
    def initialize(self) -> StorageResult:
        try:
            # Initialize storage
            self._initialized = True
            return StorageResult.success_result("Initialized")
        except Exception as e:
            return StorageResult.error_result("Init failed", e)

    def save_reflection(self, reflection: Reflection) -> StorageResult:
        # Validate first
        is_valid, error = self.validate_reflection(reflection)
        if not is_valid:
            return StorageResult.error_result(error)

        # Save logic here
        return StorageResult.success_result("Saved")

    def get_reflection(self, reflection_id: UUID) -> Optional[Reflection]:
        # Retrieval logic here
        pass

    # ... implement other abstract methods
```

---

## Testing

All types include comprehensive test coverage in `tests/`:

```bash
# Run tests
pytest packages/shared/tests/

# Run with coverage
pytest --cov=shared packages/shared/tests/
```

---

## Design Principles

1. **Type Safety**: Extensive use of dataclasses and type hints
2. **Serialization**: All types can be serialized to/from dictionaries
3. **Validation**: Input validation at type boundaries
4. **Immutability**: Clear separation of mutable and immutable data
5. **Extensibility**: Abstract interfaces for customization
6. **Documentation**: Comprehensive docstrings for all public APIs

---

## Dependencies

- Python 3.9+
- No external dependencies for core types
- Storage implementations may require additional packages

---

## Version

Current version: 0.1.0

See [CHANGELOG.md](../../CHANGELOG.md) for version history.
