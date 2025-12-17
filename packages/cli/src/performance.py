"""Performance optimization utilities."""

import functools
import time
from collections import deque
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any


class PerformanceMonitor:
    """
    Monitor and optimize CLI performance.
    """

    def __init__(self):
        """Initialize performance monitor."""
        self.metrics = {}
        self.recent_operations = deque(maxlen=100)

    def time_operation(self, operation_name: str) -> Callable:
        """
        Decorator to time an operation.

        Args:
            operation_name: Name of the operation

        Returns:
            Decorated function
        """

        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.perf_counter()
                result = func(*args, **kwargs)
                end_time = time.perf_counter()

                duration_ms = (end_time - start_time) * 1000

                # Record metric
                if operation_name not in self.metrics:
                    self.metrics[operation_name] = []

                self.metrics[operation_name].append(duration_ms)

                # Record recent operation
                self.recent_operations.append(
                    {
                        "operation": operation_name,
                        "duration_ms": duration_ms,
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                    }
                )

                return result

            return wrapper

        return decorator

    def get_average_duration(self, operation_name: str) -> float:
        """
        Get average duration for an operation.

        Args:
            operation_name: Name of the operation

        Returns:
            Average duration in milliseconds
        """
        durations = self.metrics.get(operation_name, [])
        if not durations:
            return 0.0

        return sum(durations) / len(durations)

    def get_stats(self, operation_name: str) -> dict[str, Any]:
        """
        Get detailed statistics for an operation.

        Args:
            operation_name: Name of the operation

        Returns:
            Statistics dictionary
        """
        durations = self.metrics.get(operation_name, [])
        if not durations:
            return {"count": 0, "average": 0, "min": 0, "max": 0}

        return {
            "count": len(durations),
            "average": sum(durations) / len(durations),
            "min": min(durations),
            "max": max(durations),
            "total": sum(durations),
        }

    def report(self) -> dict[str, Any]:
        """
        Generate performance report.

        Returns:
            Performance report dictionary
        """
        report = {"operations": {}, "recent_operations": list(self.recent_operations)}

        for operation_name in self.metrics:
            report["operations"][operation_name] = self.get_stats(operation_name)

        return report


class CacheManager:
    """
    Manage caching for improved performance.
    """

    def __init__(self, ttl_seconds: int = 300):
        """
        Initialize cache manager.

        Args:
            ttl_seconds: Time-to-live for cache entries in seconds
        """
        self.cache = {}
        self.ttl_seconds = ttl_seconds

    def get(self, key: str) -> Any:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value, or None if not found or expired
        """
        if key not in self.cache:
            return None

        entry = self.cache[key]
        expiry = entry["timestamp"] + timedelta(seconds=self.ttl_seconds)

        if datetime.utcnow() > expiry:
            # Expired
            del self.cache[key]
            return None

        return entry["value"]

    def set(self, key: str, value: Any) -> None:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
        """
        self.cache[key] = {"value": value, "timestamp": datetime.utcnow()}

    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()

    def cleanup_expired(self) -> int:
        """
        Remove expired cache entries.

        Returns:
            Number of entries removed
        """
        now = datetime.utcnow()
        expired_keys = []

        for key, entry in self.cache.items():
            expiry = entry["timestamp"] + timedelta(seconds=self.ttl_seconds)
            if now > expiry:
                expired_keys.append(key)

        for key in expired_keys:
            del self.cache[key]

        return len(expired_keys)


# Global performance monitor
_monitor = PerformanceMonitor()


def timed(operation_name: str) -> Callable:
    """
    Decorator to time an operation using global monitor.

    Args:
        operation_name: Name of the operation

    Returns:
        Decorated function
    """
    return _monitor.time_operation(operation_name)


def get_performance_report() -> dict[str, Any]:
    """
    Get global performance report.

    Returns:
        Performance report dictionary
    """
    return _monitor.report()
