"""Grade completeness queries and quality metrics aggregation.

Implements grade coverage analysis, missing grade tracking, and quality
metrics calculation for dashboards and reporting.

US-044: Enhanced Data Quality for Multi-Source Grades - Phase 3
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy import select, func, and_, or_, distinct
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class GradeCompletenessAnalyzer:
    """Analyzes grade coverage and completeness across prospects and sources."""
    
    def __init__(self, session: Session):
        """Initialize analyzer with database session.
        
        Args:
            session: SQLAlchemy Session for database queries
        """
        self.session = session
    
    def get_total_prospects_by_position(self, position: Optional[str] = None) -> Dict[str, int]:
        """Get total prospect count by position.
        
        Args:
            position: Specific position to filter (or None for all)
            
        Returns:
            Dictionary of {position: count}
        """
        from src.backend.database.models import Prospect
        
        query = select(Prospect.position, func.count(Prospect.id)).where(
            Prospect.status == "active"
        ).group_by(Prospect.position)
        
        if position:
            query = query.where(Prospect.position == position)
        
        results = self.session.execute(query).all()
        return {pos: count for pos, count in results}
    
    def get_prospects_with_grades_by_source(
        self,
        grade_source: str,
        position: Optional[str] = None,
        after_date: Optional[datetime] = None,
    ) -> int:
        """Count prospects with grades from specific source.
        
        Args:
            grade_source: Grade source ("pff", "espn", "nfl", "yahoo")
            position: Position filter (optional)
            after_date: Only grades after this date (optional)
            
        Returns:
            Count of prospects with grades from source
        """
        from src.backend.database.models import Prospect, ProspectGrade
        
        query = select(func.count(distinct(ProspectGrade.prospect_id))).where(
            ProspectGrade.source == grade_source
        )
        
        if position:
            query = query.join(Prospect).where(Prospect.position == position)
        
        if after_date:
            query = query.where(ProspectGrade.grade_date >= after_date)
        
        result = self.session.execute(query).scalar()
        return result or 0
    
    def get_grade_coverage_by_source(
        self,
        position: Optional[str] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """Calculate grade coverage percentage by source.
        
        Args:
            position: Position to analyze (None = all positions)
            
        Returns:
            Dictionary of {source: {count, percentage, total_prospects}}
        """
        # Get total prospects for position
        total_by_pos = self.get_total_prospects_by_position(position)
        total_prospects = sum(total_by_pos.values()) if position is None else total_by_pos.get(position, 0)
        
        if total_prospects == 0:
            return {}
        
        # Get counts by source
        sources = ["pff", "espn", "nfl", "yahoo"]
        coverage = {}
        
        for source in sources:
            count = self.get_prospects_with_grades_by_source(source, position)
            percentage = (count / total_prospects * 100) if total_prospects > 0 else 0
            
            coverage[source] = {
                "count": count,
                "percentage": round(percentage, 1),
                "total_prospects": total_prospects,
                "missing": total_prospects - count,
            }
        
        return coverage
    
    def get_grade_coverage_by_position(
        self,
        grade_source: str,
    ) -> Dict[str, Dict[str, Any]]:
        """Calculate grade coverage percentage by position.
        
        Args:
            grade_source: Grade source to analyze
            
        Returns:
            Dictionary of {position: {count, percentage, total_prospects}}
        """
        from src.backend.database.models import Prospect, ProspectGrade
        
        # Get total prospects by position
        total_by_pos = self.get_total_prospects_by_position()
        
        if not total_by_pos:
            return {}
        
        # Get counts by position for source
        query = select(
            Prospect.position,
            func.count(distinct(ProspectGrade.prospect_id))
        ).join(
            ProspectGrade, Prospect.id == ProspectGrade.prospect_id
        ).where(
            ProspectGrade.source == grade_source
        ).group_by(
            Prospect.position
        )
        
        results = self.session.execute(query).all()
        coverage_by_source = {pos: count for pos, count in results}
        
        # Calculate coverage
        coverage = {}
        for position, total in total_by_pos.items():
            count = coverage_by_source.get(position, 0)
            percentage = (count / total * 100) if total > 0 else 0
            
            coverage[position] = {
                "count": count,
                "percentage": round(percentage, 1),
                "total_prospects": total,
                "missing": total - count,
            }
        
        return coverage
    
    def get_missing_grades_by_position(
        self,
        grade_source: str,
        position: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get list of prospects missing grades from specific source.
        
        Args:
            grade_source: Source to check for missing grades
            position: Position filter (optional)
            
        Returns:
            List of prospect dicts with name, position, college
        """
        from src.backend.database.models import Prospect, ProspectGrade
        
        # Subquery: prospects with grades from source
        has_grade = select(ProspectGrade.prospect_id).where(
            ProspectGrade.source == grade_source
        ).distinct()
        
        # Main query: prospects without grades
        query = select(Prospect).where(
            and_(
                Prospect.status == "active",
                ~Prospect.id.in_(has_grade)
            )
        )
        
        if position:
            query = query.where(Prospect.position == position)
        
        prospects = self.session.execute(query).scalars().all()
        
        return [
            {
                "prospect_id": str(p.id),
                "name": p.name,
                "position": p.position,
                "college": p.college,
            }
            for p in prospects
        ]
    
    def get_grade_freshness_by_source(
        self,
        grade_source: str,
        position: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Analyze grade freshness (how recent are the grades).
        
        Args:
            grade_source: Source to analyze
            position: Position filter (optional)
            
        Returns:
            Dictionary with freshness metrics
        """
        from src.backend.database.models import ProspectGrade, Prospect
        
        query = select(
            func.max(ProspectGrade.grade_date).label("newest_grade"),
            func.min(ProspectGrade.grade_date).label("oldest_grade"),
            func.avg(ProspectGrade.grade_date).label("avg_grade_date"),
            func.count(ProspectGrade.id).label("total_grades"),
        ).where(
            ProspectGrade.source == grade_source
        )
        
        if position:
            query = query.join(Prospect).where(Prospect.position == position)
        
        result = self.session.execute(query).first()
        
        if not result or result.total_grades == 0:
            return {
                "newest_grade": None,
                "oldest_grade": None,
                "days_since_newest": None,
                "days_since_oldest": None,
                "total_grades": 0,
            }
        
        now = datetime.utcnow()
        newest = result.newest_grade
        oldest = result.oldest_grade
        
        return {
            "newest_grade": newest.isoformat() if newest else None,
            "oldest_grade": oldest.isoformat() if oldest else None,
            "days_since_newest": (now - newest).days if newest else None,
            "days_since_oldest": (now - oldest).days if oldest else None,
            "total_grades": result.total_grades,
        }
    
    def get_grade_sources_per_prospect(
        self,
        position: Optional[str] = None,
        min_sources: int = 0,
    ) -> Dict[str, int]:
        """Analyze how many sources each prospect has grades from.
        
        Args:
            position: Position filter (optional)
            min_sources: Only include prospects with at least this many sources
            
        Returns:
            Dictionary of {num_sources: count_of_prospects}
        """
        from src.backend.database.models import Prospect, ProspectGrade
        
        # Count unique sources per prospect
        query = select(
            ProspectGrade.prospect_id,
            func.count(distinct(ProspectGrade.source)).label("num_sources")
        ).group_by(
            ProspectGrade.prospect_id
        )
        
        if position:
            query = query.join(Prospect).where(Prospect.position == position)
        
        if min_sources > 0:
            query = query.having(func.count(distinct(ProspectGrade.source)) >= min_sources)
        
        results = self.session.execute(query).all()
        
        # Aggregate counts
        distribution = {}
        for prospect_id, num_sources in results:
            distribution[num_sources] = distribution.get(num_sources, 0) + 1
        
        return distribution
    
    def calculate_quality_metrics(
        self,
        metric_date: Optional[datetime] = None,
        position: Optional[str] = None,
        grade_source: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Calculate comprehensive quality metrics for a position/source.
        
        Args:
            metric_date: Date to calculate metrics for (default: today)
            position: Position group (None = all positions)
            grade_source: Grade source (None = all sources)
            
        Returns:
            Dictionary with all quality metrics
        """
        if metric_date is None:
            metric_date = datetime.utcnow()
        
        from src.backend.database.models import ProspectGrade
        
        # Get total prospects
        total_by_pos = self.get_total_prospects_by_position(position)
        total_prospects = sum(total_by_pos.values()) if position is None else total_by_pos.get(position, 0)
        
        # Get coverage
        if grade_source:
            # Single source
            count_with_grades = self.get_prospects_with_grades_by_source(grade_source, position)
            total_grades = self.session.execute(
                select(func.count(ProspectGrade.id)).where(
                    ProspectGrade.source == grade_source
                )
            ).scalar() or 0
        else:
            # All sources
            count_with_grades = self.session.execute(
                select(func.count(distinct(ProspectGrade.prospect_id))).where(
                    ProspectGrade.source.in_(["pff", "espn", "nfl", "yahoo"])
                )
            ).scalar() or 0
            total_grades = self.session.execute(
                select(func.count(ProspectGrade.id))
            ).scalar() or 0
        
        coverage_pct = (count_with_grades / total_prospects * 100) if total_prospects > 0 else 0
        validation_pct = 100.0  # Placeholder - will be calculated in Phase 4
        
        # Get outlier count (from grade_history table if available)
        try:
            from src.data_pipeline.models.quality import GradeHistory
            outliers = self.session.execute(
                select(func.count(GradeHistory.history_id)).where(
                    GradeHistory.is_outlier == True
                )
            ).scalar() or 0
        except:
            outliers = 0
        
        outlier_pct = (outliers / total_grades * 100) if total_grades > 0 else 0
        
        # Get alert count (from quality_alerts table if available)
        try:
            from src.data_pipeline.models.quality import QualityAlert
            alerts = self.session.execute(
                select(func.count(QualityAlert.alert_id))
            ).scalar() or 0
        except:
            alerts = 0
        
        # Calculate quality score (0-100)
        # Formula: (coverage * 0.4) + (validation_pct * 0.4) + ((100 - outlier_pct) * 0.2)
        quality_score = round(
            (coverage_pct * 0.4) + (validation_pct * 0.4) + ((100 - outlier_pct) * 0.2),
            1
        )
        
        return {
            "metric_date": metric_date.isoformat(),
            "position": position,
            "grade_source": grade_source,
            "total_prospects": total_prospects,
            "prospects_with_grades": count_with_grades,
            "coverage_percentage": round(coverage_pct, 1),
            "total_grades_loaded": total_grades,
            "grades_validated": total_grades,  # Placeholder
            "validation_percentage": round(validation_pct, 1),
            "outliers_detected": outliers,
            "outlier_percentage": round(outlier_pct, 1),
            "critical_outliers": 0,  # Will be counted in Phase 4
            "alerts_generated": alerts,
            "alerts_reviewed": 0,  # Placeholder
            "alerts_escalated": 0,  # Placeholder
            "quality_score": quality_score,
        }
    
    def get_completeness_summary(self) -> Dict[str, Any]:
        """Get complete summary of grade completeness across all dimensions.
        
        Returns:
            Comprehensive summary with coverage by source, by position, etc.
        """
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "coverage_by_source": self.get_grade_coverage_by_source(),
            "coverage_by_position_pff": self.get_grade_coverage_by_position("pff"),
            "coverage_by_position_espn": self.get_grade_coverage_by_position("espn"),
            "missing_pff_grades": self.get_missing_grades_by_position("pff"),
            "freshness_pff": self.get_grade_freshness_by_source("pff"),
            "freshness_espn": self.get_grade_freshness_by_source("espn"),
            "source_distribution": self.get_grade_sources_per_prospect(),
        }
