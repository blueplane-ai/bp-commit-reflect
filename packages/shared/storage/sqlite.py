"""
SQLite storage backend for the Commit Reflection System.

This module implements the SQLite storage backend with proper schema,
indices, migrations, and connection pooling.
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from uuid import UUID
from contextlib import contextmanager

from ..types.storage import (
    StorageBackend,
    StorageResult,
    StorageError,
    StorageConnectionError,
    StorageWriteError,
    StorageReadError,
    QueryOptions,
    SortOrder,
)
from ..types.reflection import Reflection


# Database schema version for migrations
SCHEMA_VERSION = 1


class SQLiteStorage(StorageBackend):
    """
    SQLite storage backend implementation.

    Provides persistent, queryable storage with indices for performance.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize SQLite storage backend.

        Args:
            config: Configuration including 'path' for database file
        """
        super().__init__(config)
        self.db_path = Path(config.get('path', '~/.commit-reflect/reflections.db')).expanduser()
        self.connection = None

    @contextmanager
    def get_connection(self):
        """
        Get a database connection with proper resource management.

        Yields:
            sqlite3.Connection object
        """
        if not self._initialized:
            raise StorageConnectionError("Storage backend not initialized")

        conn = None
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            # Enable foreign keys
            conn.execute("PRAGMA foreign_keys = ON")
            yield conn
        except sqlite3.Error as e:
            raise StorageConnectionError(f"Failed to connect to database: {e}")
        finally:
            if conn:
                conn.close()

    def initialize(self) -> StorageResult:
        """
        Initialize the SQLite database with schema and indices.

        Returns:
            StorageResult indicating success or failure
        """
        try:
            # Ensure parent directory exists
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

            # Create database and schema
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Create schema version table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS schema_version (
                        version INTEGER PRIMARY KEY,
                        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Check current schema version
                cursor.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
                current_version = cursor.fetchone()
                current_version = current_version[0] if current_version else 0

                # Apply migrations if needed
                if current_version < SCHEMA_VERSION:
                    self._apply_migrations(conn, current_version)

                conn.commit()

            self._initialized = True
            return StorageResult.success_result("SQLite storage initialized")

        except Exception as e:
            return StorageResult.error_result(f"Failed to initialize SQLite storage: {e}", error=e)

    def _apply_migrations(self, conn: sqlite3.Connection, from_version: int):
        """
        Apply database migrations from current version to latest.

        Args:
            conn: Database connection
            from_version: Current schema version
        """
        cursor = conn.cursor()

        # Migration to version 1: Initial schema
        if from_version < 1:
            # Reflections table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reflections (
                    id TEXT PRIMARY KEY,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    project_name TEXT,
                    commit_hash TEXT NOT NULL,
                    commit_message TEXT NOT NULL,
                    branch TEXT NOT NULL,
                    author_name TEXT NOT NULL,
                    author_email TEXT NOT NULL,
                    commit_timestamp TIMESTAMP NOT NULL,
                    files_changed INTEGER DEFAULT 0,
                    insertions INTEGER DEFAULT 0,
                    deletions INTEGER DEFAULT 0,
                    changed_files TEXT,
                    session_id TEXT NOT NULL,
                    session_started_at TIMESTAMP NOT NULL,
                    session_completed_at TIMESTAMP,
                    tool_version TEXT,
                    environment TEXT,
                    interrupted INTEGER DEFAULT 0,
                    additional_context TEXT
                )
            """)

            # Answers table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS answers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reflection_id TEXT NOT NULL,
                    question_id TEXT NOT NULL,
                    question_text TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    answered_at TIMESTAMP NOT NULL,
                    metadata TEXT,
                    FOREIGN KEY (reflection_id) REFERENCES reflections(id) ON DELETE CASCADE
                )
            """)

            # Indices for performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_reflections_created_at
                ON reflections(created_at)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_reflections_project_name
                ON reflections(project_name)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_reflections_commit_hash
                ON reflections(commit_hash)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_reflections_branch
                ON reflections(branch)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_reflections_author_email
                ON reflections(author_email)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_answers_reflection_id
                ON answers(reflection_id)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_answers_question_id
                ON answers(question_id)
            """)

            # Record migration
            cursor.execute("INSERT INTO schema_version (version) VALUES (1)")

    def close(self) -> StorageResult:
        """
        Close database connections and clean up resources.

        Returns:
            StorageResult indicating success or failure
        """
        try:
            # Connection pooling would be cleaned up here
            self._initialized = False
            return StorageResult.success_result("SQLite storage closed")
        except Exception as e:
            return StorageResult.error_result(f"Error closing SQLite storage: {e}", error=e)

    def save_reflection(self, reflection: Reflection) -> StorageResult:
        """
        Save a reflection to the SQLite database.

        Args:
            reflection: The reflection to save

        Returns:
            StorageResult indicating success or failure
        """
        try:
            # Validate reflection
            is_valid, error_msg = self.validate_reflection(reflection)
            if not is_valid:
                return StorageResult.error_result(f"Invalid reflection: {error_msg}")

            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Check if reflection exists
                cursor.execute("SELECT id FROM reflections WHERE id = ?", (str(reflection.id),))
                exists = cursor.fetchone()

                # Prepare data
                ctx = reflection.commit_context
                meta = reflection.session_metadata

                if exists:
                    # Update existing reflection
                    cursor.execute("""
                        UPDATE reflections SET
                            updated_at = ?,
                            project_name = ?,
                            commit_hash = ?,
                            commit_message = ?,
                            branch = ?,
                            author_name = ?,
                            author_email = ?,
                            commit_timestamp = ?,
                            files_changed = ?,
                            insertions = ?,
                            deletions = ?,
                            changed_files = ?,
                            session_id = ?,
                            session_started_at = ?,
                            session_completed_at = ?,
                            tool_version = ?,
                            environment = ?,
                            interrupted = ?,
                            additional_context = ?
                        WHERE id = ?
                    """, (
                        reflection.updated_at,
                        meta.project_name,
                        ctx.commit_hash,
                        ctx.commit_message,
                        ctx.branch,
                        ctx.author_name,
                        ctx.author_email,
                        ctx.timestamp,
                        ctx.files_changed,
                        ctx.insertions,
                        ctx.deletions,
                        json.dumps(ctx.changed_files),
                        str(meta.session_id),
                        meta.started_at,
                        meta.completed_at,
                        meta.tool_version,
                        meta.environment,
                        1 if meta.interrupted else 0,
                        json.dumps(meta.additional_context) if meta.additional_context else None,
                        str(reflection.id),
                    ))

                    # Delete old answers
                    cursor.execute("DELETE FROM answers WHERE reflection_id = ?", (str(reflection.id),))
                else:
                    # Insert new reflection
                    cursor.execute("""
                        INSERT INTO reflections (
                            id, created_at, updated_at, project_name,
                            commit_hash, commit_message, branch, author_name, author_email,
                            commit_timestamp, files_changed, insertions, deletions, changed_files,
                            session_id, session_started_at, session_completed_at,
                            tool_version, environment, interrupted, additional_context
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        str(reflection.id),
                        reflection.created_at,
                        reflection.updated_at,
                        meta.project_name,
                        ctx.commit_hash,
                        ctx.commit_message,
                        ctx.branch,
                        ctx.author_name,
                        ctx.author_email,
                        ctx.timestamp,
                        ctx.files_changed,
                        ctx.insertions,
                        ctx.deletions,
                        json.dumps(ctx.changed_files),
                        str(meta.session_id),
                        meta.started_at,
                        meta.completed_at,
                        meta.tool_version,
                        meta.environment,
                        1 if meta.interrupted else 0,
                        json.dumps(meta.additional_context) if meta.additional_context else None,
                    ))

                # Insert answers
                for answer in reflection.answers:
                    cursor.execute("""
                        INSERT INTO answers (
                            reflection_id, question_id, question_text, answer, answered_at, metadata
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        str(reflection.id),
                        answer.question_id,
                        answer.question_text,
                        answer.answer,
                        answer.answered_at,
                        json.dumps(answer.metadata) if answer.metadata else None,
                    ))

                conn.commit()

            return StorageResult.success_result("Reflection saved successfully")

        except Exception as e:
            raise StorageWriteError(f"Failed to save reflection: {e}")

    def get_reflection(self, reflection_id: UUID) -> Optional[Reflection]:
        """
        Retrieve a reflection by ID.

        Args:
            reflection_id: UUID of the reflection to retrieve

        Returns:
            The reflection if found, None otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Get reflection
                cursor.execute("SELECT * FROM reflections WHERE id = ?", (str(reflection_id),))
                row = cursor.fetchone()

                if not row:
                    return None

                # Get answers
                cursor.execute(
                    "SELECT * FROM answers WHERE reflection_id = ? ORDER BY answered_at",
                    (str(reflection_id),)
                )
                answer_rows = cursor.fetchall()

                return self._row_to_reflection(row, answer_rows)

        except Exception as e:
            raise StorageReadError(f"Failed to get reflection: {e}")

    def query_reflections(self, options: QueryOptions) -> List[Reflection]:
        """
        Query reflections based on options.

        Args:
            options: Query options for filtering and sorting

        Returns:
            List of reflections matching the query
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Build query
                query = "SELECT * FROM reflections WHERE 1=1"
                params = []

                # Apply filters
                if options.project_name:
                    query += " AND project_name = ?"
                    params.append(options.project_name)

                if options.branch:
                    query += " AND branch = ?"
                    params.append(options.branch)

                if options.author_email:
                    query += " AND author_email = ?"
                    params.append(options.author_email)

                if options.date_from:
                    query += " AND created_at >= ?"
                    params.append(options.date_from)

                if options.date_to:
                    query += " AND created_at <= ?"
                    params.append(options.date_to)

                if options.filter_by:
                    for key, value in options.filter_by.items():
                        query += f" AND {key} = ?"
                        params.append(value)

                # Apply sorting
                sort_order = "DESC" if options.sort_order == SortOrder.DESC else "ASC"
                query += f" ORDER BY {options.sort_by} {sort_order}"

                # Apply pagination
                if options.limit:
                    query += " LIMIT ?"
                    params.append(options.limit)

                if options.offset:
                    query += " OFFSET ?"
                    params.append(options.offset)

                # Execute query
                cursor.execute(query, params)
                rows = cursor.fetchall()

                # Convert rows to reflections
                reflections = []
                for row in rows:
                    # Get answers for this reflection
                    cursor.execute(
                        "SELECT * FROM answers WHERE reflection_id = ? ORDER BY answered_at",
                        (row['id'],)
                    )
                    answer_rows = cursor.fetchall()

                    reflection = self._row_to_reflection(row, answer_rows)
                    if reflection:
                        reflections.append(reflection)

                return reflections

        except Exception as e:
            raise StorageReadError(f"Failed to query reflections: {e}")

    def delete_reflection(self, reflection_id: UUID) -> StorageResult:
        """
        Delete a reflection from storage.

        Args:
            reflection_id: UUID of the reflection to delete

        Returns:
            StorageResult indicating success or failure
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Delete reflection (answers cascade)
                cursor.execute("DELETE FROM reflections WHERE id = ?", (str(reflection_id),))

                if cursor.rowcount == 0:
                    return StorageResult.error_result("Reflection not found")

                conn.commit()

            return StorageResult.success_result("Reflection deleted successfully")

        except Exception as e:
            raise StorageWriteError(f"Failed to delete reflection: {e}")

    def count_reflections(self, filter_by: Optional[Dict[str, Any]] = None) -> int:
        """
        Count reflections matching optional filters.

        Args:
            filter_by: Optional filters to apply

        Returns:
            Number of reflections matching filters
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                query = "SELECT COUNT(*) FROM reflections WHERE 1=1"
                params = []

                if filter_by:
                    for key, value in filter_by.items():
                        query += f" AND {key} = ?"
                        params.append(value)

                cursor.execute(query, params)
                count = cursor.fetchone()[0]

                return count

        except Exception as e:
            raise StorageReadError(f"Failed to count reflections: {e}")

    def health_check(self) -> StorageResult:
        """
        Check if the storage backend is healthy and accessible.

        Returns:
            StorageResult indicating health status
        """
        try:
            if not self._initialized:
                return StorageResult.error_result("Storage not initialized")

            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")

            return StorageResult.success_result("SQLite storage is healthy")

        except Exception as e:
            return StorageResult.error_result(f"SQLite storage is unhealthy: {e}", error=e)

    def _row_to_reflection(self, row: sqlite3.Row, answer_rows: List[sqlite3.Row]) -> Optional[Reflection]:
        """
        Convert database row to Reflection object.

        Args:
            row: Reflection row from database
            answer_rows: Answer rows for this reflection

        Returns:
            Reflection object or None if conversion fails
        """
        try:
            from ..types.reflection import ReflectionAnswer, CommitContext, SessionMetadata

            # Parse answers
            answers = []
            for answer_row in answer_rows:
                answer = ReflectionAnswer(
                    question_id=answer_row['question_id'],
                    question_text=answer_row['question_text'],
                    answer=answer_row['answer'],
                    answered_at=datetime.fromisoformat(answer_row['answered_at']),
                    metadata=json.loads(answer_row['metadata']) if answer_row['metadata'] else None,
                )
                answers.append(answer)

            # Parse commit context
            commit_context = CommitContext(
                commit_hash=row['commit_hash'],
                commit_message=row['commit_message'],
                branch=row['branch'],
                author_name=row['author_name'],
                author_email=row['author_email'],
                timestamp=datetime.fromisoformat(row['commit_timestamp']),
                files_changed=row['files_changed'] or 0,
                insertions=row['insertions'] or 0,
                deletions=row['deletions'] or 0,
                changed_files=json.loads(row['changed_files']) if row['changed_files'] else [],
            )

            # Parse session metadata
            session_metadata = SessionMetadata(
                session_id=UUID(row['session_id']),
                started_at=datetime.fromisoformat(row['session_started_at']),
                completed_at=datetime.fromisoformat(row['session_completed_at'])
                    if row['session_completed_at'] else None,
                project_name=row['project_name'],
                tool_version=row['tool_version'],
                environment=row['environment'],
                interrupted=bool(row['interrupted']),
                additional_context=json.loads(row['additional_context'])
                    if row['additional_context'] else None,
            )

            # Create reflection
            reflection = Reflection(
                id=UUID(row['id']),
                answers=answers,
                commit_context=commit_context,
                session_metadata=session_metadata,
                created_at=datetime.fromisoformat(row['created_at']),
                updated_at=datetime.fromisoformat(row['updated_at']),
            )

            return reflection

        except Exception as e:
            raise StorageReadError(f"Failed to convert row to reflection: {e}")
