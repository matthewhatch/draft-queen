"""Daily quality metrics calculation and persistence job.

Scheduled task that runs daily to calculate quality metrics for all
positions and sources, storing results for dashboard visualization.

US-044: Enhanced Data Quality for Multi-Source Grades - Phase 3
"""

import logging
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class QualityMetricsJob:
    """Daily job to calculate and persist quality metrics."""
    
    def __init__(self, session: Session):
        """Initialize job with database session.
        
        Args:
            session: SQLAlchemy Session for database operations
        """
        self.session = session
        from src.data_pipeline.quality.grade_completeness import GradeCompletenessAnalyzer
        from src.data_pipeline.quality.metrics_aggregator import QualityMetricsAggregator
        
        self.analyzer = GradeCompletenessAnalyzer(session)
        self.aggregator = QualityMetricsAggregator(session)
    
    def run(
        self,
        metric_date: Optional[datetime] = None,
        specific_position: Optional[str] = None,
        specific_source: Optional[str] = None,
        dry_run: bool = False,
    ) -> dict:
        """Run daily quality metrics calculation.
        
        Args:
            metric_date: Date to calculate metrics for (default: today)
            specific_position: Only calculate for specific position (optional)
            specific_source: Only calculate for specific source (optional)
            dry_run: If True, calculate but don't persist
            
        Returns:
            Summary of calculated metrics
        """
        if metric_date is None:
            metric_date = datetime.utcnow()
        
        logger.info(f"Starting quality metrics job for {metric_date.date()}")
        
        try:
            # Get all positions and sources to calculate
            all_positions = self._get_positions_to_calculate(specific_position)
            all_sources = self._get_sources_to_calculate(specific_source)
            
            metrics_saved = 0
            metrics_summary = []
            
            # 1. Calculate by position (all sources combined)
            for position in all_positions:
                metrics = self.analyzer.calculate_quality_metrics(
                    metric_date=metric_date,
                    position=position,
                    grade_source=None,  # All sources
                )
                
                if not dry_run:
                    self.aggregator.save_quality_metric(
                        metric_date=metric_date,
                        position=position,
                        grade_source=None,
                        metric_data=metrics,
                    )
                    metrics_saved += 1
                
                metrics_summary.append({
                    "type": "by_position",
                    "position": position,
                    "quality_score": metrics.get("quality_score", 0),
                    "coverage_percentage": metrics.get("coverage_percentage", 0),
                })
            
            # 2. Calculate by source (all positions combined)
            for source in all_sources:
                metrics = self.analyzer.calculate_quality_metrics(
                    metric_date=metric_date,
                    position=None,  # All positions
                    grade_source=source,
                )
                
                if not dry_run:
                    self.aggregator.save_quality_metric(
                        metric_date=metric_date,
                        position=None,
                        grade_source=source,
                        metric_data=metrics,
                    )
                    metrics_saved += 1
                
                metrics_summary.append({
                    "type": "by_source",
                    "source": source,
                    "quality_score": metrics.get("quality_score", 0),
                    "coverage_percentage": metrics.get("coverage_percentage", 0),
                })
            
            # 3. Calculate cross-tabulation (position x source)
            for position in all_positions:
                for source in all_sources:
                    metrics = self.analyzer.calculate_quality_metrics(
                        metric_date=metric_date,
                        position=position,
                        grade_source=source,
                    )
                    
                    if not dry_run:
                        self.aggregator.save_quality_metric(
                            metric_date=metric_date,
                            position=position,
                            grade_source=source,
                            metric_data=metrics,
                        )
                        metrics_saved += 1
                    
                    metrics_summary.append({
                        "type": "cross_tab",
                        "position": position,
                        "source": source,
                        "quality_score": metrics.get("quality_score", 0),
                        "coverage_percentage": metrics.get("coverage_percentage", 0),
                    })
            
            # 4. Cleanup old metrics (keep 90 days)
            if not dry_run:
                try:
                    deleted = self.aggregator.cleanup_old_metrics(days_to_keep=90)
                    logger.info(f"Cleaned up {deleted} old quality metrics")
                except Exception as e:
                    logger.warning(f"Cleanup failed: {e}")
            
            result = {
                "status": "success" if not dry_run else "dry_run",
                "metric_date": metric_date.isoformat(),
                "metrics_saved": metrics_saved,
                "metrics_summary": metrics_summary,
                "positions_calculated": len(all_positions),
                "sources_calculated": len(all_sources),
            }
            
            logger.info(
                f"Quality metrics job completed: "
                f"{metrics_saved} metrics saved, "
                f"{len(all_positions)} positions, {len(all_sources)} sources"
            )
            
            return result
        
        except Exception as e:
            logger.error(f"Quality metrics job failed: {e}", exc_info=True)
            raise
    
    def _get_positions_to_calculate(self, specific_position: Optional[str] = None) -> List[str]:
        """Get list of positions to calculate metrics for.
        
        Args:
            specific_position: If provided, only return this position
            
        Returns:
            List of position codes
        """
        if specific_position:
            return [specific_position]
        
        # Get all active positions from database
        from src.backend.database.models import Prospect
        from sqlalchemy import select, distinct
        
        query = select(distinct(Prospect.position)).where(
            Prospect.status == "active"
        ).order_by(Prospect.position)
        
        positions = self.session.execute(query).scalars().all()
        return list(positions) if positions else []
    
    def _get_sources_to_calculate(self, specific_source: Optional[str] = None) -> List[str]:
        """Get list of sources to calculate metrics for.
        
        Args:
            specific_source: If provided, only return this source
            
        Returns:
            List of source names
        """
        if specific_source:
            return [specific_source]
        
        # Standard sources
        return ["pff", "espn", "nfl", "yahoo"]


def create_quality_metrics_job(session: Session) -> QualityMetricsJob:
    """Factory function to create quality metrics job.
    
    Args:
        session: SQLAlchemy Session
        
    Returns:
        QualityMetricsJob instance
    """
    return QualityMetricsJob(session)
