"""Quality metrics persistence and aggregation for dashboard reporting.

Handles calculation and storage of daily quality metrics for all positions,
sources, and aggregated views.

US-044: Enhanced Data Quality for Multi-Source Grades - Phase 3
"""

import logging
from datetime import datetime, date
from typing import Dict, Optional, List, Any
from sqlalchemy import select, and_
from sqlalchemy.orm import Session
from uuid import uuid4

logger = logging.getLogger(__name__)


class QualityMetricsAggregator:
    """Aggregates and persists quality metrics for dashboard."""
    
    def __init__(self, session: Session):
        """Initialize aggregator with database session.
        
        Args:
            session: SQLAlchemy Session for database queries
        """
        self.session = session
    
    def save_quality_metric(
        self,
        metric_date: datetime,
        position: Optional[str] = None,
        grade_source: Optional[str] = None,
        metric_data: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Save quality metric record to database.
        
        Args:
            metric_date: Date of metric calculation
            position: Position group (None = all positions)
            grade_source: Grade source (None = all sources)
            metric_data: Calculated metrics dictionary
            
        Returns:
            UUID of created metric record
        """
        from src.data_pipeline.models.quality import QualityMetric
        
        if metric_data is None:
            metric_data = {}
        
        try:
            metric = QualityMetric(
                metric_id=uuid4(),
                metric_date=metric_date,
                position=position,
                grade_source=grade_source,
                total_prospects=metric_data.get("total_prospects", 0),
                prospects_with_grades=metric_data.get("prospects_with_grades", 0),
                coverage_percentage=metric_data.get("coverage_percentage", 0.0),
                total_grades_loaded=metric_data.get("total_grades_loaded", 0),
                grades_validated=metric_data.get("grades_validated", 0),
                validation_percentage=metric_data.get("validation_percentage", 0.0),
                outliers_detected=metric_data.get("outliers_detected", 0),
                outlier_percentage=metric_data.get("outlier_percentage", 0.0),
                critical_outliers=metric_data.get("critical_outliers", 0),
                alerts_generated=metric_data.get("alerts_generated", 0),
                alerts_reviewed=metric_data.get("alerts_reviewed", 0),
                alerts_escalated=metric_data.get("alerts_escalated", 0),
                quality_score=metric_data.get("quality_score", 100.0),
                calculation_notes=metric_data.get("calculation_notes", None),
            )
            
            self.session.add(metric)
            self.session.commit()
            
            logger.info(
                f"Saved quality metric: position={position}, source={grade_source}, "
                f"score={metric.quality_score:.1f}"
            )
            
            return str(metric.metric_id)
        
        except Exception as e:
            logger.error(f"Failed to save quality metric: {e}")
            self.session.rollback()
            raise
    
    def get_latest_quality_metrics(
        self,
        position: Optional[str] = None,
        grade_source: Optional[str] = None,
        limit: int = 30,
    ) -> List[Dict[str, Any]]:
        """Get latest quality metrics records.
        
        Args:
            position: Position filter (optional)
            grade_source: Source filter (optional)
            limit: Maximum records to return
            
        Returns:
            List of metric records
        """
        from src.data_pipeline.models.quality import QualityMetric
        
        query = select(QualityMetric).order_by(
            QualityMetric.metric_date.desc()
        ).limit(limit)
        
        if position:
            query = query.where(QualityMetric.position == position)
        
        if grade_source:
            query = query.where(QualityMetric.grade_source == grade_source)
        
        metrics = self.session.execute(query).scalars().all()
        
        return [
            {
                "metric_date": m.metric_date.isoformat(),
                "position": m.position,
                "grade_source": m.grade_source,
                "total_prospects": m.total_prospects,
                "prospects_with_grades": m.prospects_with_grades,
                "coverage_percentage": m.coverage_percentage,
                "total_grades_loaded": m.total_grades_loaded,
                "grades_validated": m.grades_validated,
                "validation_percentage": m.validation_percentage,
                "outliers_detected": m.outliers_detected,
                "outlier_percentage": m.outlier_percentage,
                "critical_outliers": m.critical_outliers,
                "alerts_generated": m.alerts_generated,
                "alerts_reviewed": m.alerts_reviewed,
                "alerts_escalated": m.alerts_escalated,
                "quality_score": m.quality_score,
            }
            for m in metrics
        ]
    
    def get_quality_trend(
        self,
        position: Optional[str] = None,
        grade_source: Optional[str] = None,
        days: int = 30,
    ) -> List[Dict[str, Any]]:
        """Get quality score trend over time.
        
        Args:
            position: Position filter (optional)
            grade_source: Source filter (optional)
            days: Number of days to look back
            
        Returns:
            List of quality metrics with quality_score
        """
        from src.data_pipeline.models.quality import QualityMetric
        from datetime import timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        query = select(
            QualityMetric.metric_date,
            QualityMetric.quality_score,
            QualityMetric.coverage_percentage,
            QualityMetric.outlier_percentage,
        ).where(
            QualityMetric.metric_date >= cutoff_date
        ).order_by(
            QualityMetric.metric_date.asc()
        )
        
        if position:
            query = query.where(QualityMetric.position == position)
        
        if grade_source:
            query = query.where(QualityMetric.grade_source == grade_source)
        
        results = self.session.execute(query).all()
        
        return [
            {
                "date": r.metric_date.isoformat(),
                "quality_score": r.quality_score,
                "coverage_percentage": r.coverage_percentage,
                "outlier_percentage": r.outlier_percentage,
            }
            for r in results
        ]
    
    def get_quality_summary_by_position(
        self,
        metric_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Get quality metrics summary grouped by position.
        
        Args:
            metric_date: Specific date to get metrics for (default: latest)
            
        Returns:
            List of metrics grouped by position
        """
        from src.data_pipeline.models.quality import QualityMetric
        
        query = select(QualityMetric).where(
            QualityMetric.grade_source.is_(None)  # All-sources view
        ).order_by(
            QualityMetric.metric_date.desc()
        )
        
        if metric_date:
            query = query.where(QualityMetric.metric_date >= metric_date)
        
        metrics = self.session.execute(query).scalars().all()
        
        # Group by position
        by_position = {}
        for m in metrics:
            if m.position not in by_position:
                by_position[m.position] = {
                    "position": m.position,
                    "total_prospects": m.total_prospects,
                    "prospects_with_grades": m.prospects_with_grades,
                    "coverage_percentage": m.coverage_percentage,
                    "quality_score": m.quality_score,
                    "outlier_percentage": m.outlier_percentage,
                    "alerts_generated": m.alerts_generated,
                    "latest_date": m.metric_date.isoformat(),
                }
        
        return list(by_position.values())
    
    def get_quality_summary_by_source(
        self,
        metric_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Get quality metrics summary grouped by source.
        
        Args:
            metric_date: Specific date to get metrics for (default: latest)
            
        Returns:
            List of metrics grouped by source
        """
        from src.data_pipeline.models.quality import QualityMetric
        
        query = select(QualityMetric).where(
            QualityMetric.position.is_(None)  # All-positions view
        ).order_by(
            QualityMetric.metric_date.desc()
        )
        
        if metric_date:
            query = query.where(QualityMetric.metric_date >= metric_date)
        
        metrics = self.session.execute(query).scalars().all()
        
        # Group by source
        by_source = {}
        for m in metrics:
            if m.grade_source not in by_source:
                by_source[m.grade_source] = {
                    "grade_source": m.grade_source,
                    "total_prospects": m.total_prospects,
                    "prospects_with_grades": m.prospects_with_grades,
                    "coverage_percentage": m.coverage_percentage,
                    "quality_score": m.quality_score,
                    "outlier_percentage": m.outlier_percentage,
                    "alerts_generated": m.alerts_generated,
                    "latest_date": m.metric_date.isoformat(),
                }
        
        return list(by_source.values())
    
    def get_quality_dashboard_summary(
        self,
        metric_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get complete dashboard summary combining all views.
        
        Args:
            metric_date: Specific date to get metrics for (default: latest)
            
        Returns:
            Complete dashboard summary with all metrics
        """
        if metric_date is None:
            metric_date = datetime.utcnow()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "metric_date": metric_date.isoformat(),
            "by_position": self.get_quality_summary_by_position(metric_date),
            "by_source": self.get_quality_summary_by_source(metric_date),
            "recent_metrics": self.get_latest_quality_metrics(limit=10),
            "trend_30_days": self.get_quality_trend(days=30),
        }
    
    def cleanup_old_metrics(self, days_to_keep: int = 90) -> int:
        """Remove quality metrics older than specified days.
        
        Args:
            days_to_keep: Keep metrics from last N days
            
        Returns:
            Count of deleted records
        """
        from src.data_pipeline.models.quality import QualityMetric
        from datetime import timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        try:
            query = select(QualityMetric).where(
                QualityMetric.metric_date < cutoff_date
            )
            old_metrics = self.session.execute(query).scalars().all()
            count = len(old_metrics)
            
            for metric in old_metrics:
                self.session.delete(metric)
            
            self.session.commit()
            logger.info(f"Cleaned up {count} old quality metrics")
            return count
        
        except Exception as e:
            logger.error(f"Failed to cleanup old metrics: {e}")
            self.session.rollback()
            raise
