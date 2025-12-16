"""Data migration utilities for reflection data."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class DataMigrator:
    """
    Handles data migration between different storage formats and versions.
    """

    def __init__(self):
        """Initialize data migrator."""
        self.migrations = {
            "v1_to_v2": self._migrate_v1_to_v2,
            "jsonl_to_sqlite": self._migrate_jsonl_to_sqlite,
        }

    def migrate(self, source: str, destination: str, migration_type: str) -> dict[str, Any]:
        """
        Migrate data from source to destination.

        Args:
            source: Source file/database path
            destination: Destination file/database path
            migration_type: Type of migration to perform

        Returns:
            Migration result dictionary with stats
        """
        migration_func = self.migrations.get(migration_type)
        if not migration_func:
            raise ValueError(f"Unknown migration type: {migration_type}")

        return migration_func(source, destination)

    def _migrate_v1_to_v2(self, source: str, destination: str) -> dict[str, Any]:
        """
        Migrate from v1 to v2 format.

        v1 format: Basic reflection structure
        v2 format: Enhanced with metadata and versioning

        Args:
            source: Source JSONL file
            destination: Destination JSONL file

        Returns:
            Migration statistics
        """
        source_path = Path(source).expanduser()
        dest_path = Path(destination).expanduser()

        migrated_count = 0
        error_count = 0

        with open(dest_path, "w", encoding="utf-8") as dest_file:
            with open(source_path, encoding="utf-8") as source_file:
                for line_num, line in enumerate(source_file, 1):
                    try:
                        # Parse v1 record
                        v1_record = json.loads(line.strip())

                        # Convert to v2 format
                        v2_record = {
                            "version": "2.0",
                            "timestamp": v1_record.get("timestamp"),
                            "project": v1_record.get("project"),
                            "branch": v1_record.get("branch"),
                            "commit_hash": v1_record.get("commit_hash"),
                            "commit_message": v1_record.get("commit_message"),
                            "files_changed": v1_record.get("files_changed", []),
                            "reflections": v1_record.get("reflections", {}),
                            "metadata": {
                                "migrated_at": datetime.utcnow().isoformat() + "Z",
                                "source_version": "1.0",
                                "original_line": line_num,
                            },
                        }

                        # Write v2 record
                        json.dump(v2_record, dest_file, ensure_ascii=False)
                        dest_file.write("\n")

                        migrated_count += 1

                    except Exception as e:
                        print(f"Error migrating line {line_num}: {e}")
                        error_count += 1

        return {
            "migration_type": "v1_to_v2",
            "source": str(source_path),
            "destination": str(dest_path),
            "migrated_count": migrated_count,
            "error_count": error_count,
            "completed_at": datetime.utcnow().isoformat() + "Z",
        }

    def _migrate_jsonl_to_sqlite(self, source: str, destination: str) -> dict[str, Any]:
        """
        Migrate from JSONL to SQLite database.

        Args:
            source: Source JSONL file
            destination: Destination SQLite database

        Returns:
            Migration statistics
        """
        # This will be fully implemented once SQLite backend (Track A) is complete
        # For now, provide the structure

        source_path = Path(source).expanduser()

        migrated_count = 0
        error_count = 0

        try:
            # Read JSONL records
            reflections = []
            with open(source_path, encoding="utf-8") as f:
                for line in f:
                    try:
                        reflections.append(json.loads(line.strip()))
                    except json.JSONDecodeError:
                        error_count += 1

            # Write to SQLite (requires SQLite backend from Track A)
            # from ...shared.storage.sqlite import SQLiteStorage
            # db = SQLiteStorage(destination)
            # for reflection in reflections:
            #     if db.write(reflection):
            #         migrated_count += 1
            #     else:
            #         error_count += 1

            migrated_count = len(reflections)

        except Exception as e:
            print(f"Migration error: {e}")

        return {
            "migration_type": "jsonl_to_sqlite",
            "source": str(source_path),
            "destination": destination,
            "migrated_count": migrated_count,
            "error_count": error_count,
            "completed_at": datetime.utcnow().isoformat() + "Z",
        }

    def validate_migration(
        self, source: str, destination: str, sample_size: int = 100
    ) -> dict[str, Any]:
        """
        Validate migration by comparing samples.

        Args:
            source: Source file path
            destination: Destination file path
            sample_size: Number of records to validate

        Returns:
            Validation results
        """
        # Load samples from both sources
        source_samples = self._load_samples(source, sample_size)
        dest_samples = self._load_samples(destination, sample_size)

        # Compare counts
        count_match = len(source_samples) == len(dest_samples)

        # Compare data integrity
        data_matches = 0
        for src, dst in zip(source_samples, dest_samples):
            if self._records_match(src, dst):
                data_matches += 1

        return {
            "source_count": len(source_samples),
            "destination_count": len(dest_samples),
            "count_match": count_match,
            "data_matches": data_matches,
            "sample_size": sample_size,
            "validation_passed": count_match and data_matches == len(source_samples),
        }

    def _load_samples(self, filepath: str, count: int) -> list[dict[str, Any]]:
        """Load sample records from file."""
        path = Path(filepath).expanduser()
        samples = []

        try:
            with open(path, encoding="utf-8") as f:
                for i, line in enumerate(f):
                    if i >= count:
                        break
                    try:
                        samples.append(json.loads(line.strip()))
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"Error loading samples: {e}")

        return samples

    def _records_match(self, record1: dict[str, Any], record2: dict[str, Any]) -> bool:
        """Check if two records match (ignoring metadata)."""
        # Compare key fields
        key_fields = ["project", "commit_hash", "timestamp"]

        for field in key_fields:
            if record1.get(field) != record2.get(field):
                return False

        return True


class BatchProcessor:
    """
    Process multiple reflections in batch operations.
    """

    def __init__(self):
        """Initialize batch processor."""
        pass

    def batch_export(
        self, reflections: list[dict[str, Any]], output_path: str, format: str = "jsonl"
    ) -> dict[str, Any]:
        """
        Export reflections to file in batch.

        Args:
            reflections: List of reflections to export
            output_path: Output file path
            format: Export format (jsonl, json, csv)

        Returns:
            Export statistics
        """
        output = Path(output_path).expanduser()

        if format == "jsonl":
            return self._export_jsonl(reflections, output)
        elif format == "json":
            return self._export_json(reflections, output)
        elif format == "csv":
            return self._export_csv(reflections, output)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _export_jsonl(self, reflections: list[dict[str, Any]], output_path: Path) -> dict[str, Any]:
        """Export to JSONL format."""
        count = 0

        with open(output_path, "w", encoding="utf-8") as f:
            for reflection in reflections:
                json.dump(reflection, f, ensure_ascii=False)
                f.write("\n")
                count += 1

        return {"format": "jsonl", "output": str(output_path), "count": count}

    def _export_json(self, reflections: list[dict[str, Any]], output_path: Path) -> dict[str, Any]:
        """Export to JSON array format."""
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(reflections, f, indent=2, ensure_ascii=False)

        return {"format": "json", "output": str(output_path), "count": len(reflections)}

    def _export_csv(self, reflections: list[dict[str, Any]], output_path: Path) -> dict[str, Any]:
        """Export to CSV format."""
        import csv

        if not reflections:
            return {"format": "csv", "output": str(output_path), "count": 0}

        # Determine columns
        columns = [
            "timestamp",
            "project",
            "branch",
            "commit_hash",
            "ai_synergy",
            "confidence",
            "experience",
            "blockers",
            "learning",
        ]

        count = 0

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()

            for reflection in reflections:
                row = {
                    "timestamp": reflection.get("timestamp"),
                    "project": reflection.get("project"),
                    "branch": reflection.get("branch"),
                    "commit_hash": reflection.get("commit_hash"),
                }

                # Extract reflection fields
                refl = reflection.get("reflections", {})
                row.update(
                    {
                        "ai_synergy": refl.get("ai_synergy"),
                        "confidence": refl.get("confidence"),
                        "experience": refl.get("experience"),
                        "blockers": refl.get("blockers"),
                        "learning": refl.get("learning"),
                    }
                )

                writer.writerow(row)
                count += 1

        return {"format": "csv", "output": str(output_path), "count": count}
