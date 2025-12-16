"""
Data consistency verification for storage backends.

Provides tools to verify data integrity and consistency across
multiple storage backends.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from shared.types.storage import StorageBackend


@dataclass
class ConsistencyCheckResult:
    """
    Result of a consistency check operation.

    Attributes:
        is_consistent: Whether data is consistent across backends
        total_records_checked: Number of records verified
        inconsistencies: List of inconsistency details
        timestamp: When check was performed
        backends_checked: List of backend types checked
    """

    is_consistent: bool
    total_records_checked: int
    inconsistencies: list[dict]
    timestamp: datetime
    backends_checked: list[str]


class ConsistencyVerifier:
    """
    Verifies data consistency across storage backends.

    Compares data across backends to detect:
    - Missing records
    - Data mismatches
    - Corrupted data
    """

    def __init__(self, backends: list[StorageBackend]):
        """
        Initialize verifier with backend list.

        Args:
            backends: List of storage backends to verify
        """
        if len(backends) < 2:
            raise ValueError("At least two backends required for consistency check")

        self.backends = backends

    def verify_record_count(self) -> ConsistencyCheckResult:
        """
        Verify that all backends have the same number of records.

        Returns:
            Consistency check result
        """
        record_counts = {}
        inconsistencies = []

        # Get record counts from each backend
        for backend in self.backends:
            backend_type = backend.get_type()
            try:
                records = backend.read()
                record_counts[backend_type] = len(records)
            except Exception as e:
                inconsistencies.append(
                    {
                        "type": "read_error",
                        "backend": backend_type,
                        "error": str(e),
                    }
                )

        # Check if all counts match
        if record_counts:
            counts = list(record_counts.values())
            all_match = all(count == counts[0] for count in counts)

            if not all_match:
                inconsistencies.append(
                    {
                        "type": "count_mismatch",
                        "counts": record_counts,
                    }
                )

        return ConsistencyCheckResult(
            is_consistent=len(inconsistencies) == 0,
            total_records_checked=max(record_counts.values()) if record_counts else 0,
            inconsistencies=inconsistencies,
            timestamp=datetime.now(timezone.utc),
            backends_checked=[b.get_type() for b in self.backends],
        )

    def verify_record_presence(self, limit: Optional[int] = None) -> ConsistencyCheckResult:
        """
        Verify that all records exist in all backends.

        Args:
            limit: Optional limit on number of records to check

        Returns:
            Consistency check result
        """
        backend_records = {}
        inconsistencies = []

        # Get records from each backend
        for backend in self.backends:
            backend_type = backend.get_type()
            try:
                records = backend.read(limit=limit)
                # Index by commit hash
                backend_records[backend_type] = {r["commit_hash"]: r for r in records}
            except Exception as e:
                inconsistencies.append(
                    {
                        "type": "read_error",
                        "backend": backend_type,
                        "error": str(e),
                    }
                )

        if len(backend_records) < 2:
            # Can't verify without at least 2 backends
            return ConsistencyCheckResult(
                is_consistent=False,
                total_records_checked=0,
                inconsistencies=inconsistencies,
                timestamp=datetime.now(timezone.utc),
                backends_checked=[b.get_type() for b in self.backends],
            )

        # Get all commit hashes across backends
        all_hashes: set[str] = set()
        for records in backend_records.values():
            all_hashes.update(records.keys())

        # Check each hash exists in all backends
        for commit_hash in all_hashes:
            backends_with_hash = [
                backend_type
                for backend_type, records in backend_records.items()
                if commit_hash in records
            ]

            if len(backends_with_hash) != len(backend_records):
                missing_from = [
                    backend_type
                    for backend_type in backend_records.keys()
                    if backend_type not in backends_with_hash
                ]

                inconsistencies.append(
                    {
                        "type": "missing_record",
                        "commit_hash": commit_hash,
                        "present_in": backends_with_hash,
                        "missing_from": missing_from,
                    }
                )

        return ConsistencyCheckResult(
            is_consistent=len(inconsistencies) == 0,
            total_records_checked=len(all_hashes),
            inconsistencies=inconsistencies,
            timestamp=datetime.now(timezone.utc),
            backends_checked=list(backend_records.keys()),
        )

    def verify_data_integrity(self, limit: Optional[int] = None) -> ConsistencyCheckResult:
        """
        Verify that record data matches across backends.

        Compares actual record contents, not just presence.

        Args:
            limit: Optional limit on number of records to check

        Returns:
            Consistency check result
        """
        backend_records = {}
        inconsistencies = []

        # Get records from each backend
        for backend in self.backends:
            backend_type = backend.get_type()
            try:
                records = backend.read(limit=limit)
                backend_records[backend_type] = {r["commit_hash"]: r for r in records}
            except Exception as e:
                inconsistencies.append(
                    {
                        "type": "read_error",
                        "backend": backend_type,
                        "error": str(e),
                    }
                )

        if len(backend_records) < 2:
            return ConsistencyCheckResult(
                is_consistent=False,
                total_records_checked=0,
                inconsistencies=inconsistencies,
                timestamp=datetime.now(timezone.utc),
                backends_checked=[b.get_type() for b in self.backends],
            )

        # Get common commit hashes (present in all backends)
        backend_types = list(backend_records.keys())
        common_hashes = set(backend_records[backend_types[0]].keys())

        for backend_type in backend_types[1:]:
            common_hashes &= set(backend_records[backend_type].keys())

        # Compare data for each common hash
        for commit_hash in common_hashes:
            reference_record = backend_records[backend_types[0]][commit_hash]

            for backend_type in backend_types[1:]:
                current_record = backend_records[backend_type][commit_hash]

                # Compare key fields
                for key in ["what_changed", "why_changed", "timestamp"]:
                    if key in reference_record and key in current_record:
                        if reference_record[key] != current_record[key]:
                            inconsistencies.append(
                                {
                                    "type": "data_mismatch",
                                    "commit_hash": commit_hash,
                                    "field": key,
                                    "reference_backend": backend_types[0],
                                    "reference_value": reference_record[key],
                                    "mismatch_backend": backend_type,
                                    "mismatch_value": current_record[key],
                                }
                            )

        return ConsistencyCheckResult(
            is_consistent=len(inconsistencies) == 0,
            total_records_checked=len(common_hashes),
            inconsistencies=inconsistencies,
            timestamp=datetime.now(timezone.utc),
            backends_checked=backend_types,
        )

    def verify_comprehensive(
        self, limit: Optional[int] = None
    ) -> dict[str, ConsistencyCheckResult]:
        """
        Perform all consistency checks.

        Args:
            limit: Optional limit on records to check

        Returns:
            Dictionary mapping check type to result
        """
        return {
            "record_count": self.verify_record_count(),
            "record_presence": self.verify_record_presence(limit=limit),
            "data_integrity": self.verify_data_integrity(limit=limit),
        }

    def get_summary(self, results: dict[str, ConsistencyCheckResult]) -> dict[str, any]:
        """
        Get summary of consistency check results.

        Args:
            results: Results from verify_comprehensive

        Returns:
            Summary dictionary with overall status
        """
        total_inconsistencies = sum(len(result.inconsistencies) for result in results.values())

        is_consistent = all(result.is_consistent for result in results.values())

        return {
            "is_consistent": is_consistent,
            "total_checks": len(results),
            "passed_checks": sum(1 for r in results.values() if r.is_consistent),
            "total_inconsistencies": total_inconsistencies,
            "backends_checked": (
                results[list(results.keys())[0]].backends_checked if results else []
            ),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
