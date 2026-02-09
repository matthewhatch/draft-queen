"""Analytics service for prospect statistics and aggregations."""

import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from decimal import Decimal

from backend.database.models import Prospect
from backend.api.schemas import QueryFilterSchema

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for calculating prospect statistics and analytics."""

    @staticmethod
    def get_position_statistics(
        db: Session,
        position: str,
        filters: Optional[QueryFilterSchema] = None,
    ) -> Dict[str, Any]:
        """
        Get aggregated statistics for a specific position.

        Args:
            db: Database session
            position: Position code (e.g., "QB", "RB")
            filters: Optional QueryFilterSchema for additional filtering

        Returns:
            Dictionary with count, average, min, max, and percentile data
        """
        try:
            # Build base query for the position
            query = db.query(Prospect).filter(Prospect.position == position.upper())

            # Apply additional filters if provided
            if filters:
                if filters.college:
                    query = query.filter(Prospect.college == filters.college)
                if filters.height_min is not None:
                    query = query.filter(Prospect.height >= filters.height_min)
                if filters.height_max is not None:
                    query = query.filter(Prospect.height <= filters.height_max)
                if filters.weight_min is not None:
                    query = query.filter(Prospect.weight >= filters.weight_min)
                if filters.weight_max is not None:
                    query = query.filter(Prospect.weight <= filters.weight_max)
                if filters.draft_grade_min is not None:
                    query = query.filter(Prospect.draft_grade >= filters.draft_grade_min)
                if filters.draft_grade_max is not None:
                    query = query.filter(Prospect.draft_grade <= filters.draft_grade_max)

            # Get all prospects for the position to calculate percentiles in Python
            prospects = query.filter(Prospect.status == "active").all()

            if not prospects:
                return {
                    "position": position.upper(),
                    "count": 0,
                    "height": None,
                    "weight": None,
                    "draft_grade": None,
                }

            count = len(prospects)

            # Calculate statistics for each numeric field
            height_stats = AnalyticsService._calculate_field_stats(
                [float(p.height) for p in prospects if p.height],
                "feet"
            )
            weight_stats = AnalyticsService._calculate_field_stats(
                [float(p.weight) for p in prospects if p.weight],
                "lbs"
            )
            draft_grade_stats = AnalyticsService._calculate_field_stats(
                [float(p.draft_grade) for p in prospects if p.draft_grade],
                "grade"
            )

            return {
                "position": position.upper(),
                "count": count,
                "height": height_stats,
                "weight": weight_stats,
                "draft_grade": draft_grade_stats,
                "filters_applied": {
                    "college": filters.college if filters and filters.college else None,
                    "height_range": {
                        "min": float(filters.height_min) if filters and filters.height_min else None,
                        "max": float(filters.height_max) if filters and filters.height_max else None,
                    } if filters else None,
                    "weight_range": {
                        "min": filters.weight_min if filters and filters.weight_min else None,
                        "max": filters.weight_max if filters and filters.weight_max else None,
                    } if filters else None,
                    "draft_grade_range": {
                        "min": float(filters.draft_grade_min) if filters and filters.draft_grade_min else None,
                        "max": float(filters.draft_grade_max) if filters and filters.draft_grade_max else None,
                    } if filters else None,
                },
            }

        except Exception as e:
            logger.error(f"Error calculating position statistics for {position}: {e}")
            raise

    @staticmethod
    def _calculate_field_stats(
        values: list,
        unit: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate statistics for a field (min, max, avg, percentiles).

        Args:
            values: List of numeric values
            unit: Unit of measurement (e.g., "feet", "lbs", "grade")

        Returns:
            Dictionary with statistics or None if no values
        """
        if not values:
            return None

        sorted_values = sorted(values)
        count = len(sorted_values)

        return {
            "unit": unit,
            "count": count,
            "min": round(min(sorted_values), 2),
            "max": round(max(sorted_values), 2),
            "average": round(sum(sorted_values) / count, 2),
            "median": AnalyticsService._percentile(sorted_values, 50),
            "percentile_25": AnalyticsService._percentile(sorted_values, 25),
            "percentile_75": AnalyticsService._percentile(sorted_values, 75),
        }

    @staticmethod
    def _percentile(sorted_values: list, p: int) -> float:
        """
        Calculate percentile for sorted values.

        Args:
            sorted_values: Sorted list of numeric values
            p: Percentile (0-100)

        Returns:
            Percentile value rounded to 2 decimals
        """
        if not sorted_values:
            return 0.0

        # Use linear interpolation for percentile calculation
        index = (p / 100.0) * (len(sorted_values) - 1)
        lower = int(index)
        upper = lower + 1

        if upper >= len(sorted_values):
            return round(sorted_values[-1], 2)

        fraction = index - lower
        return round(
            sorted_values[lower] + fraction * (sorted_values[upper] - sorted_values[lower]),
            2
        )

    @staticmethod
    def get_all_positions_summary(db: Session) -> Dict[str, Dict[str, Any]]:
        """
        Get summary statistics for all positions.

        Args:
            db: Database session

        Returns:
            Dictionary mapping position to summary stats
        """
        try:
            # Get all unique positions
            positions = db.query(Prospect.position).distinct().filter(
                Prospect.status == "active"
            ).all()

            summary = {}
            for (position,) in positions:
                stats = AnalyticsService.get_position_statistics(db, position)
                if stats["count"] > 0:
                    summary[position] = {
                        "count": stats["count"],
                        "height_avg": stats["height"]["average"] if stats["height"] else None,
                        "weight_avg": stats["weight"]["average"] if stats["weight"] else None,
                        "draft_grade_avg": stats["draft_grade"]["average"] if stats["draft_grade"] else None,
                    }

            return summary

        except Exception as e:
            logger.error(f"Error calculating all positions summary: {e}")
            raise
