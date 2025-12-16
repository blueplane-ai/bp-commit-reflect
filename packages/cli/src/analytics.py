"""Query and analytics tools for reflection data."""

import statistics
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any


class ReflectionAnalytics:
    """
    Provides analytics and querying capabilities for reflection data.
    """

    def __init__(self, reflections: list[dict[str, Any]]):
        """
        Initialize analytics with reflection data.

        Args:
            reflections: List of reflection dictionaries
        """
        self.reflections = reflections

    def average_ai_synergy(
        self, project: str | None = None, days: int | None = None
    ) -> float | None:
        """
        Calculate average AI synergy score.

        Args:
            project: Filter by project name (optional)
            days: Only include reflections from last N days (optional)

        Returns:
            Average AI synergy score, or None if no data
        """
        filtered = self._filter_reflections(project=project, days=days)
        scores = [
            r.get("reflections", {}).get("ai_synergy")
            for r in filtered
            if r.get("reflections", {}).get("ai_synergy") is not None
        ]

        if not scores:
            return None

        return statistics.mean(scores)

    def average_confidence(
        self, project: str | None = None, days: int | None = None
    ) -> float | None:
        """
        Calculate average confidence score.

        Args:
            project: Filter by project name (optional)
            days: Only include reflections from last N days (optional)

        Returns:
            Average confidence score, or None if no data
        """
        filtered = self._filter_reflections(project=project, days=days)
        scores = [
            r.get("reflections", {}).get("confidence")
            for r in filtered
            if r.get("reflections", {}).get("confidence") is not None
        ]

        if not scores:
            return None

        return statistics.mean(scores)

    def reflection_count(self, project: str | None = None, days: int | None = None) -> int:
        """
        Count reflections matching criteria.

        Args:
            project: Filter by project name (optional)
            days: Only include reflections from last N days (optional)

        Returns:
            Number of matching reflections
        """
        filtered = self._filter_reflections(project=project, days=days)
        return len(filtered)

    def reflections_by_project(self) -> dict[str, int]:
        """
        Get reflection count grouped by project.

        Returns:
            Dictionary mapping project names to reflection counts
        """
        counts = defaultdict(int)
        for reflection in self.reflections:
            project = reflection.get("project", "unknown")
            counts[project] += 1

        return dict(counts)

    def reflections_by_branch(self, project: str | None = None) -> dict[str, int]:
        """
        Get reflection count grouped by branch.

        Args:
            project: Filter by project name (optional)

        Returns:
            Dictionary mapping branch names to reflection counts
        """
        filtered = self._filter_reflections(project=project)
        counts = defaultdict(int)

        for reflection in filtered:
            branch = reflection.get("branch", "unknown")
            counts[branch] += 1

        return dict(counts)

    def synergy_trend(
        self, project: str | None = None, window_days: int = 7
    ) -> list[dict[str, Any]]:
        """
        Calculate AI synergy trend over time.

        Args:
            project: Filter by project name (optional)
            window_days: Rolling window size in days

        Returns:
            List of {date, average_synergy} dictionaries
        """
        filtered = self._filter_reflections(project=project)

        # Group by date
        by_date = defaultdict(list)
        for reflection in filtered:
            timestamp_str = reflection.get("timestamp", "")
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                date_key = timestamp.date().isoformat()
                synergy = reflection.get("reflections", {}).get("ai_synergy")
                if synergy is not None:
                    by_date[date_key].append(synergy)
            except (ValueError, AttributeError):
                continue

        # Calculate averages
        trend = []
        for date_key, scores in sorted(by_date.items()):
            trend.append(
                {"date": date_key, "average_synergy": statistics.mean(scores), "count": len(scores)}
            )

        return trend

    def common_blockers(
        self, project: str | None = None, days: int | None = None, limit: int = 10
    ) -> list[str]:
        """
        Extract common blockers from reflections.

        Args:
            project: Filter by project name (optional)
            days: Only include reflections from last N days (optional)
            limit: Maximum number of blockers to return

        Returns:
            List of blocker descriptions
        """
        filtered = self._filter_reflections(project=project, days=days)
        blockers = []

        for reflection in filtered:
            blocker = reflection.get("reflections", {}).get("blockers")
            if blocker and blocker.strip():
                blockers.append(blocker.strip())

        return blockers[:limit]

    def learning_insights(
        self, project: str | None = None, days: int | None = None, limit: int = 10
    ) -> list[str]:
        """
        Extract learning insights from reflections.

        Args:
            project: Filter by project name (optional)
            days: Only include reflections from last N days (optional)
            limit: Maximum number of insights to return

        Returns:
            List of learning descriptions
        """
        filtered = self._filter_reflections(project=project, days=days)
        learnings = []

        for reflection in filtered:
            learning = reflection.get("reflections", {}).get("learning")
            if learning and learning.strip():
                learnings.append(learning.strip())

        return learnings[:limit]

    def summary_report(self, project: str | None = None, days: int | None = 7) -> dict[str, Any]:
        """
        Generate comprehensive summary report.

        Args:
            project: Filter by project name (optional)
            days: Only include reflections from last N days (optional)

        Returns:
            Summary report dictionary
        """
        return {
            "period_days": days,
            "project": project or "all",
            "total_reflections": self.reflection_count(project, days),
            "average_ai_synergy": self.average_ai_synergy(project, days),
            "average_confidence": self.average_confidence(project, days),
            "reflections_by_project": self.reflections_by_project(),
            "recent_blockers": self.common_blockers(project, days, limit=5),
            "recent_learnings": self.learning_insights(project, days, limit=5),
        }

    def _filter_reflections(
        self, project: str | None = None, days: int | None = None
    ) -> list[dict[str, Any]]:
        """
        Filter reflections by criteria.

        Args:
            project: Filter by project name (optional)
            days: Only include reflections from last N days (optional)

        Returns:
            Filtered list of reflections
        """
        filtered = self.reflections

        # Filter by project
        if project:
            filtered = [r for r in filtered if r.get("project") == project]

        # Filter by date
        if days:
            cutoff = datetime.utcnow() - timedelta(days=days)
            date_filtered = []

            for reflection in filtered:
                timestamp_str = reflection.get("timestamp", "")
                try:
                    timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                    if timestamp >= cutoff:
                        date_filtered.append(reflection)
                except (ValueError, AttributeError):
                    continue

            filtered = date_filtered

        return filtered


class QueryBuilder:
    """
    Builder for constructing complex queries on reflection data.
    """

    def __init__(self):
        """Initialize query builder."""
        self.filters = []
        self.sort_by = None
        self.limit_value = None

    def filter_project(self, project: str) -> "QueryBuilder":
        """Add project filter."""
        self.filters.append(lambda r: r.get("project") == project)
        return self

    def filter_branch(self, branch: str) -> "QueryBuilder":
        """Add branch filter."""
        self.filters.append(lambda r: r.get("branch") == branch)
        return self

    def filter_synergy_min(self, min_score: int) -> "QueryBuilder":
        """Add minimum AI synergy filter."""
        self.filters.append(lambda r: r.get("reflections", {}).get("ai_synergy", 0) >= min_score)
        return self

    def filter_confidence_min(self, min_score: int) -> "QueryBuilder":
        """Add minimum confidence filter."""
        self.filters.append(lambda r: r.get("reflections", {}).get("confidence", 0) >= min_score)
        return self

    def sort(self, field: str, reverse: bool = False) -> "QueryBuilder":
        """Add sort criteria."""
        self.sort_by = (field, reverse)
        return self

    def limit(self, n: int) -> "QueryBuilder":
        """Add result limit."""
        self.limit_value = n
        return self

    def execute(self, reflections: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Execute query on reflection data.

        Args:
            reflections: List of reflections to query

        Returns:
            Filtered and sorted results
        """
        results = reflections

        # Apply filters
        for filter_func in self.filters:
            results = [r for r in results if filter_func(r)]

        # Apply sorting
        if self.sort_by:
            field, reverse = self.sort_by
            results = sorted(results, key=lambda r: r.get(field, ""), reverse=reverse)

        # Apply limit
        if self.limit_value:
            results = results[: self.limit_value]

        return results
