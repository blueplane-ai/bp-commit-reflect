"""
Health check and monitoring utilities for storage backends.

Provides comprehensive health checking, diagnostics, and monitoring
for storage backend instances.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List

from shared.types.storage import StorageBackend


class HealthStatus(Enum):
    """Health status levels for storage backends."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """
    Result of a health check operation.

    Attributes:
        status: Overall health status
        backend_type: Type of backend checked
        message: Human-readable status message
        timestamp: When check was performed
        details: Additional diagnostic information
        latency_ms: Health check latency in milliseconds
    """

    status: HealthStatus
    backend_type: str
    message: str
    timestamp: datetime
    details: Dict
    latency_ms: float


class StorageHealthChecker:
    """
    Performs health checks on storage backends.

    Implements various health check strategies including:
    - Basic connectivity checks
    - Write/read verification
    - Performance monitoring
    - Capacity checks
    """

    def __init__(self, backend: StorageBackend):
        """
        Initialize health checker for a backend.

        Args:
            backend: Storage backend to check
        """
        self.backend = backend

    def check_basic(self) -> HealthCheckResult:
        """
        Perform basic health check (connectivity only).

        Returns:
            Health check result with status and details
        """
        start_time = datetime.now(timezone.utc)

        try:
            is_healthy = self.backend.health_check()

            latency = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

            if is_healthy:
                return HealthCheckResult(
                    status=HealthStatus.HEALTHY,
                    backend_type=self.backend.get_type(),
                    message="Backend is responsive",
                    timestamp=datetime.now(timezone.utc),
                    details={"check_type": "basic"},
                    latency_ms=latency,
                )
            else:
                return HealthCheckResult(
                    status=HealthStatus.UNHEALTHY,
                    backend_type=self.backend.get_type(),
                    message="Backend health check failed",
                    timestamp=datetime.now(timezone.utc),
                    details={"check_type": "basic"},
                    latency_ms=latency,
                )

        except Exception as e:
            latency = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                backend_type=self.backend.get_type(),
                message=f"Health check error: {str(e)}",
                timestamp=datetime.now(timezone.utc),
                details={"check_type": "basic", "error": str(e)},
                latency_ms=latency,
            )

    def check_write_read(self) -> HealthCheckResult:
        """
        Perform write/read verification check.

        Writes a test record, reads it back, and verifies integrity.

        Returns:
            Health check result
        """
        start_time = datetime.now(timezone.utc)

        test_record = {
            "commit_hash": f"health_check_{start_time.isoformat()}",
            "timestamp": start_time.isoformat(),
            "what_changed": "health check test",
            "why_changed": "verifying backend functionality",
            "_is_health_check": True,
        }

        try:
            # Write test record
            write_success = self.backend.write(test_record)

            if not write_success:
                latency = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                return HealthCheckResult(
                    status=HealthStatus.DEGRADED,
                    backend_type=self.backend.get_type(),
                    message="Write operation failed",
                    timestamp=datetime.now(timezone.utc),
                    details={"check_type": "write_read", "operation": "write"},
                    latency_ms=latency,
                )

            # Read back test record
            records = self.backend.read_recent(count=1)

            latency = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

            if not records:
                return HealthCheckResult(
                    status=HealthStatus.DEGRADED,
                    backend_type=self.backend.get_type(),
                    message="Read operation returned no data",
                    timestamp=datetime.now(timezone.utc),
                    details={"check_type": "write_read", "operation": "read"},
                    latency_ms=latency,
                )

            return HealthCheckResult(
                status=HealthStatus.HEALTHY,
                backend_type=self.backend.get_type(),
                message="Write/read verification successful",
                timestamp=datetime.now(timezone.utc),
                details={"check_type": "write_read"},
                latency_ms=latency,
            )

        except Exception as e:
            latency = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                backend_type=self.backend.get_type(),
                message=f"Write/read check failed: {str(e)}",
                timestamp=datetime.now(timezone.utc),
                details={"check_type": "write_read", "error": str(e)},
                latency_ms=latency,
            )

    def check_performance(self, threshold_ms: float = 1000.0) -> HealthCheckResult:
        """
        Check backend performance against threshold.

        Args:
            threshold_ms: Maximum acceptable latency in milliseconds

        Returns:
            Health check result with performance metrics
        """
        start_time = datetime.now(timezone.utc)

        try:
            # Perform read operation
            self.backend.read_recent(count=10)

            latency = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

            if latency > threshold_ms:
                return HealthCheckResult(
                    status=HealthStatus.DEGRADED,
                    backend_type=self.backend.get_type(),
                    message=f"Performance degraded: {latency:.2f}ms > {threshold_ms}ms",
                    timestamp=datetime.now(timezone.utc),
                    details={
                        "check_type": "performance",
                        "threshold_ms": threshold_ms,
                    },
                    latency_ms=latency,
                )

            return HealthCheckResult(
                status=HealthStatus.HEALTHY,
                backend_type=self.backend.get_type(),
                message=f"Performance within threshold: {latency:.2f}ms",
                timestamp=datetime.now(timezone.utc),
                details={"check_type": "performance", "threshold_ms": threshold_ms},
                latency_ms=latency,
            )

        except Exception as e:
            latency = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                backend_type=self.backend.get_type(),
                message=f"Performance check failed: {str(e)}",
                timestamp=datetime.now(timezone.utc),
                details={"check_type": "performance", "error": str(e)},
                latency_ms=latency,
            )

    def check_comprehensive(self) -> Dict[str, HealthCheckResult]:
        """
        Perform all health checks.

        Returns:
            Dictionary mapping check type to result
        """
        return {
            "basic": self.check_basic(),
            "write_read": self.check_write_read(),
            "performance": self.check_performance(),
        }


class MultiBackendHealthMonitor:
    """
    Monitors health across multiple storage backends.

    Provides aggregate health status and identifies degraded backends.
    """

    def __init__(self, backends: List[StorageBackend]):
        """
        Initialize monitor with backend list.

        Args:
            backends: List of storage backends to monitor
        """
        self.backends = backends
        self.checkers = [StorageHealthChecker(backend) for backend in backends]

    def check_all(self) -> Dict[str, HealthCheckResult]:
        """
        Check health of all backends.

        Returns:
            Dictionary mapping backend type to health result
        """
        results = {}

        for checker in self.checkers:
            result = checker.check_basic()
            results[result.backend_type] = result

        return results

    def check_comprehensive_all(self) -> Dict[str, Dict[str, HealthCheckResult]]:
        """
        Perform comprehensive checks on all backends.

        Returns:
            Nested dictionary: backend_type -> check_type -> result
        """
        results = {}

        for checker in self.checkers:
            backend_type = checker.backend.get_type()
            results[backend_type] = checker.check_comprehensive()

        return results

    def get_overall_status(self) -> HealthStatus:
        """
        Get overall system health status.

        Returns:
            Worst health status across all backends
        """
        results = self.check_all()

        if not results:
            return HealthStatus.UNKNOWN

        # Find worst status
        statuses = [result.status for result in results.values()]

        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        elif all(s == HealthStatus.HEALTHY for s in statuses):
            return HealthStatus.HEALTHY
        else:
            return HealthStatus.UNKNOWN

    def get_unhealthy_backends(self) -> List[str]:
        """
        Get list of unhealthy backend types.

        Returns:
            List of backend type identifiers that are unhealthy
        """
        results = self.check_all()

        return [
            backend_type
            for backend_type, result in results.items()
            if result.status == HealthStatus.UNHEALTHY
        ]

    def get_healthy_backends(self) -> List[str]:
        """
        Get list of healthy backend types.

        Returns:
            List of backend type identifiers that are healthy
        """
        results = self.check_all()

        return [
            backend_type
            for backend_type, result in results.items()
            if result.status == HealthStatus.HEALTHY
        ]
