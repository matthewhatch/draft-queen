"""Ranking service for prospect scoring and sorting."""

import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc, and_
from decimal import Decimal
from enum import Enum

from backend.database.models import Prospect
from backend.api.schemas import QueryFilterSchema

logger = logging.getLogger(__name__)


class RankingMetric(str, Enum):
    """Available ranking metrics."""
    DRAFT_GRADE = "draft_grade"
    HEIGHT = "height"
    WEIGHT = "weight"
    ROUND_PROJECTION = "round_projection"


class RankingService:
    """Service for ranking and scoring prospects."""

    # Metric column mapping
    METRIC_COLUMNS = {
        "draft_grade": Prospect.draft_grade,
        "height": Prospect.height,
        "weight": Prospect.weight,
        "round_projection": Prospect.round_projection,
    }

    @staticmethod
    def get_top_prospects(
        db: Session,
        position: Optional[str] = None,
        metric: str = "draft_grade",
        limit: int = 10,
        sort_order: str = "desc",
        filters: Optional[QueryFilterSchema] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get top prospects ranked by a specific metric.

        Args:
            db: Database session
            position: Optional position filter
            metric: Metric to rank by (draft_grade, height, weight, round_projection)
            limit: Number of top prospects to return (max 100)
            sort_order: "asc" or "desc"
            filters: Optional additional QueryFilterSchema filters

        Returns:
            List of prospects sorted by metric
        """
        try:
            # Validate inputs
            if metric not in RankingService.METRIC_COLUMNS:
                raise ValueError(f"Unknown metric: {metric}. Available: {list(RankingService.METRIC_COLUMNS.keys())}")
            
            if limit < 1 or limit > 100:
                limit = min(max(limit, 1), 100)
            
            if sort_order.lower() not in ["asc", "desc"]:
                sort_order = "desc"

            # Build query
            query = db.query(Prospect).filter(Prospect.status == "active")

            # Apply position filter if provided
            if position:
                query = query.filter(Prospect.position == position.upper())

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

            # Get metric column
            metric_column = RankingService.METRIC_COLUMNS[metric]

            # Sort by metric
            if sort_order.lower() == "desc":
                query = query.order_by(desc(metric_column))
            else:
                query = query.order_by(asc(metric_column))

            # Apply limit
            prospects = query.limit(limit).all()

            # Convert to dictionaries with rank
            results = []
            for rank, prospect in enumerate(prospects, 1):
                results.append({
                    "rank": rank,
                    "name": prospect.name,
                    "position": prospect.position,
                    "college": prospect.college,
                    "height": float(prospect.height) if prospect.height else None,
                    "weight": prospect.weight,
                    "draft_grade": float(prospect.draft_grade) if prospect.draft_grade else None,
                    "round_projection": prospect.round_projection,
                    f"{metric}_value": float(getattr(prospect, metric)) if getattr(prospect, metric) else None,
                })

            return results

        except Exception as e:
            logger.error(f"Error ranking prospects: {e}")
            raise

    @staticmethod
    def get_composite_score(
        db: Session,
        position: Optional[str] = None,
        metrics: Optional[List[str]] = None,
        weights: Optional[List[float]] = None,
        limit: int = 10,
        filters: Optional[QueryFilterSchema] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get top prospects ranked by a weighted composite score.

        Args:
            db: Database session
            position: Optional position filter
            metrics: List of metrics to use (default: ["draft_grade", "height", "weight"])
            weights: List of weights for each metric (must sum to 1.0)
            limit: Number of top prospects to return
            filters: Optional additional filters

        Returns:
            List of prospects sorted by composite score
        """
        try:
            # Set defaults
            if metrics is None:
                metrics = ["draft_grade", "height", "weight"]
            
            if weights is None:
                # Equal weighting
                weights = [1.0 / len(metrics)] * len(metrics)

            # Validate
            if len(metrics) != len(weights):
                raise ValueError("Metrics and weights must have same length")
            
            if abs(sum(weights) - 1.0) > 0.01:
                raise ValueError("Weights must sum to approximately 1.0")

            # Validate metrics
            for metric in metrics:
                if metric not in RankingService.METRIC_COLUMNS:
                    raise ValueError(f"Unknown metric: {metric}")

            # Build query for active prospects
            query = db.query(Prospect).filter(Prospect.status == "active")

            if position:
                query = query.filter(Prospect.position == position.upper())

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

            prospects = query.all()

            if not prospects:
                return []

            # Calculate scores with normalization
            scores = []
            for prospect in prospects:
                prospect_metrics = {}
                normalized_score = 0.0

                for i, metric in enumerate(metrics):
                    value = getattr(prospect, metric)
                    if value is None:
                        value = 0.0
                    
                    prospect_metrics[metric] = float(value)

                    # Normalize to 0-100 scale based on min/max in dataset
                    min_val = min(float(getattr(p, metric) or 0) for p in prospects)
                    max_val = max(float(getattr(p, metric) or 0) for p in prospects)

                    if max_val > min_val:
                        normalized = ((float(value) - min_val) / (max_val - min_val)) * 100
                    else:
                        normalized = 50.0

                    normalized_score += normalized * weights[i]

                scores.append({
                    "prospect": prospect,
                    "score": round(normalized_score, 2),
                    "metrics": prospect_metrics,
                })

            # Sort by score (descending)
            scores.sort(key=lambda x: x["score"], reverse=True)

            # Format results
            results = []
            for rank, item in enumerate(scores[:limit], 1):
                prospect = item["prospect"]
                results.append({
                    "rank": rank,
                    "name": prospect.name,
                    "position": prospect.position,
                    "college": prospect.college,
                    "height": float(prospect.height) if prospect.height else None,
                    "weight": prospect.weight,
                    "draft_grade": float(prospect.draft_grade) if prospect.draft_grade else None,
                    "round_projection": prospect.round_projection,
                    "composite_score": item["score"],
                    "component_scores": item["metrics"],
                    "weights": {metric: weight for metric, weight in zip(metrics, weights)},
                })

            return results

        except Exception as e:
            logger.error(f"Error calculating composite score: {e}")
            raise
