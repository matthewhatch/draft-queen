"""
CFR-005: Analytics & Quality Dashboards

Comprehensive analytics and quality monitoring for CFR (College Football Reference) integration.

This module provides:
1. CFR-specific quality metrics calculation
2. Match rate and accuracy analytics
3. Position-specific performance analysis
4. Dashboard data endpoints
5. Quality alerts and thresholds
6. Historical trend tracking

Quality Metrics Tracked:
- Total prospects scraped vs matched
- Match accuracy by position
- Data completeness by field
- Duplicate detection
- Outlier identification
- Parse error rate
- Data quality score (0-100)

Analytics Features:
- Match rate trends over time
- Position-specific performance
- College distribution analysis
- Season-specific statistics
- Recursive aggregations for drill-down
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from uuid import UUID
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = logging.getLogger(__name__)


class CFRQualityStatus(Enum):
    """CFR data quality status levels."""
    EXCELLENT = "excellent"  # >95%
    GOOD = "good"  # 90-95%
    WARNING = "warning"  # 80-90%
    CRITICAL = "critical"  # <80%


class CFRAnalyticsCalculator:
    """Calculate analytics metrics for CFR-sourced data."""

    def __init__(self, db: AsyncSession):
        """Initialize analytics calculator.
        
        Args:
            db: Database session
        """
        self.db = db

    async def get_cfr_quality_metrics(
        self,
        extraction_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """Calculate CFR-specific quality metrics.
        
        Args:
            extraction_id: Specific extraction to analyze (None = latest)
            
        Returns:
            Dict with comprehensive quality metrics
        """
        try:
            logger.info("Calculating CFR quality metrics...")
            
            # Get staging and canonical record counts
            staging_count = await self._get_staging_count(extraction_id)
            matched_count = await self._get_matched_count(extraction_id)
            total_loaded = await self._get_total_loaded(extraction_id)
            
            # Calculate rates
            match_rate = (
                (matched_count / staging_count * 100) 
                if staging_count > 0 else 0.0
            )
            load_success_rate = (
                (total_loaded / matched_count * 100)
                if matched_count > 0 else 0.0
            )
            
            # Get field-level completeness
            completeness = await self._get_field_completeness()
            
            # Get outlier count
            outliers = await self._get_outlier_count()
            
            # Get parse error count
            errors = await self._get_parse_error_count()
            
            # Calculate overall quality score
            quality_score = self._calculate_quality_score(
                match_rate,
                load_success_rate,
                completeness,
                outliers,
                errors,
            )
            
            # Determine status
            if quality_score >= 95:
                status = CFRQualityStatus.EXCELLENT
            elif quality_score >= 90:
                status = CFRQualityStatus.GOOD
            elif quality_score >= 80:
                status = CFRQualityStatus.WARNING
            else:
                status = CFRQualityStatus.CRITICAL
            
            logger.info(f"✓ Quality metrics calculated: {status.value}")
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "extraction_id": str(extraction_id) if extraction_id else "latest",
                "staging_count": staging_count,
                "matched_count": matched_count,
                "total_loaded": total_loaded,
                "match_rate": round(match_rate, 2),
                "load_success_rate": round(load_success_rate, 2),
                "field_completeness": completeness,
                "outlier_count": outliers,
                "parse_error_count": errors,
                "overall_quality_score": round(quality_score, 2),
                "status": status.value,
            }
            
        except Exception as e:
            logger.error(f"Error calculating CFR quality metrics: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    async def _get_staging_count(self, extraction_id: Optional[UUID] = None) -> int:
        """Get count of staged CFR records."""
        try:
            if extraction_id:
                result = await self.db.execute(
                    text("""
                        SELECT COUNT(*) as count 
                        FROM cfr_staging 
                        WHERE extraction_id = :extraction_id
                    """),
                    {"extraction_id": extraction_id}
                )
            else:
                result = await self.db.execute(
                    text("SELECT COUNT(*) as count FROM cfr_staging")
                )
            
            return result.scalar() or 0
        except Exception as e:
            logger.warning(f"Error getting staging count: {e}")
            return 0

    async def _get_matched_count(self, extraction_id: Optional[UUID] = None) -> int:
        """Get count of successfully matched CFR records."""
        try:
            if extraction_id:
                result = await self.db.execute(
                    text("""
                        SELECT COUNT(DISTINCT pcs.id) as count 
                        FROM prospect_college_stats pcs
                        JOIN data_lineage dl ON pcs.id = dl.entity_id
                        WHERE dl.extraction_id = :extraction_id 
                        AND pcs.season >= 2020
                    """),
                    {"extraction_id": extraction_id}
                )
            else:
                result = await self.db.execute(
                    text("""
                        SELECT COUNT(*) as count 
                        FROM prospect_college_stats 
                        WHERE season >= 2020
                    """)
                )
            
            return result.scalar() or 0
        except Exception as e:
            logger.warning(f"Error getting matched count: {e}")
            return 0

    async def _get_total_loaded(self, extraction_id: Optional[UUID] = None) -> int:
        """Get total records loaded to prospect_college_stats."""
        try:
            result = await self.db.execute(
                text("SELECT COUNT(*) as count FROM prospect_college_stats")
            )
            return result.scalar() or 0
        except Exception as e:
            logger.warning(f"Error getting total loaded: {e}")
            return 0

    async def _get_field_completeness(self) -> Dict[str, float]:
        """Get completeness percentage for key CFR fields."""
        try:
            result = await self.db.execute(
                text("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(passing_yards) as passing_yards,
                        COUNT(rushing_yards) as rushing_yards,
                        COUNT(receiving_yards) as receiving_yards,
                        COUNT(tackles) as tackles,
                        COUNT(sacks) as sacks
                    FROM prospect_college_stats
                    WHERE season >= 2020
                """)
            )
            
            row = result.fetchone()
            if not row or row[0] == 0:
                return {
                    "passing_yards": 0.0,
                    "rushing_yards": 0.0,
                    "receiving_yards": 0.0,
                    "tackles": 0.0,
                    "sacks": 0.0,
                }
            
            total = row[0]
            return {
                "passing_yards": round((row[1] / total) * 100, 2),
                "rushing_yards": round((row[2] / total) * 100, 2),
                "receiving_yards": round((row[3] / total) * 100, 2),
                "tackles": round((row[4] / total) * 100, 2),
                "sacks": round((row[5] / total) * 100, 2),
            }
        except Exception as e:
            logger.warning(f"Error getting field completeness: {e}")
            return {}

    async def _get_outlier_count(self) -> int:
        """Get count of statistical outliers."""
        try:
            # Outliers: stats > 3 std deviations from mean
            result = await self.db.execute(
                text("""
                    SELECT COUNT(*) as count
                    FROM prospect_college_stats
                    WHERE season >= 2020
                    AND (
                        passing_yards > (SELECT AVG(passing_yards) + 3 * STDDEV(passing_yards) 
                                        FROM prospect_college_stats WHERE season >= 2020)
                        OR receiving_yards > (SELECT AVG(receiving_yards) + 3 * STDDEV(receiving_yards) 
                                            FROM prospect_college_stats WHERE season >= 2020)
                        OR rushing_yards > (SELECT AVG(rushing_yards) + 3 * STDDEV(rushing_yards) 
                                          FROM prospect_college_stats WHERE season >= 2020)
                    )
                """)
            )
            return result.scalar() or 0
        except Exception as e:
            logger.warning(f"Error getting outlier count: {e}")
            return 0

    async def _get_parse_error_count(self) -> int:
        """Get count of parse errors from staging."""
        try:
            result = await self.db.execute(
                text("""
                    SELECT COUNT(*) as count 
                    FROM cfr_staging 
                    WHERE extraction_notes LIKE '%error%' 
                    OR extraction_notes LIKE '%failed%'
                """)
            )
            return result.scalar() or 0
        except Exception as e:
            logger.warning(f"Error getting parse error count: {e}")
            return 0

    @staticmethod
    def _calculate_quality_score(
        match_rate: float,
        load_success_rate: float,
        completeness: Dict[str, float],
        outliers: int,
        errors: int,
    ) -> float:
        """Calculate overall quality score (0-100).
        
        Score formula:
        - Match rate: 40%
        - Load success: 30%
        - Field completeness: 20%
        - Outlier count: 5% (penalize high outlier count)
        - Error count: 5% (penalize high error count)
        """
        match_score = match_rate * 0.40
        load_score = load_success_rate * 0.30
        
        # Average completeness across fields
        avg_completeness = (
            sum(completeness.values()) / len(completeness)
            if completeness else 0.0
        )
        completeness_score = avg_completeness * 0.20
        
        # Outlier penalty (fewer = better)
        outlier_score = max(0, 5.0 - (outliers * 0.1))
        
        # Error penalty (fewer = better)
        error_score = max(0, 5.0 - (errors * 0.1))
        
        total_score = match_score + load_score + completeness_score + outlier_score + error_score
        return min(100.0, max(0.0, total_score))


class CFRDashboardData:
    """Provide dashboard data for CFR analytics."""

    def __init__(self, db: AsyncSession):
        """Initialize dashboard data provider.
        
        Args:
            db: Database session
        """
        self.db = db
        self.calculator = CFRAnalyticsCalculator(db)

    async def get_dashboard_summary(self) -> Dict[str, Any]:
        """Get complete dashboard summary.
        
        Returns:
            Dict with all dashboard metrics
        """
        logger.info("Building CFR dashboard summary...")
        
        try:
            quality_metrics = await self.calculator.get_cfr_quality_metrics()
            position_stats = await self._get_position_statistics()
            college_stats = await self._get_college_statistics()
            trends = await self._get_30day_trends()
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "quality_metrics": quality_metrics,
                "position_statistics": position_stats,
                "college_statistics": college_stats,
                "trends_30_days": trends,
                "status": "success",
            }
        except Exception as e:
            logger.error(f"Error building dashboard summary: {e}")
            return {"error": str(e), "status": "failed"}

    async def _get_position_statistics(self) -> List[Dict[str, Any]]:
        """Get CFR statistics breakdown by position."""
        try:
            result = await self.db.execute(
                text("""
                    SELECT 
                        position,
                        COUNT(*) as total_prospects,
                        COUNT(passing_yards) as with_passing,
                        COUNT(rushing_yards) as with_rushing,
                        COUNT(receiving_yards) as with_receiving,
                        COUNT(tackles) as with_defense,
                        ROUND(AVG(CAST(passing_yards AS NUMERIC)), 2) as avg_passing,
                        ROUND(AVG(CAST(rushing_yards AS NUMERIC)), 2) as avg_rushing,
                        ROUND(AVG(CAST(receiving_yards AS NUMERIC)), 2) as avg_receiving,
                        ROUND(AVG(CAST(tackles AS NUMERIC)), 2) as avg_tackles
                    FROM prospect_college_stats
                    WHERE season >= 2020
                    GROUP BY position
                    ORDER BY total_prospects DESC
                """)
            )
            
            positions = []
            for row in result.fetchall():
                positions.append({
                    "position": row[0],
                    "total_prospects": row[1],
                    "with_passing": row[2],
                    "with_rushing": row[3],
                    "with_receiving": row[4],
                    "with_defense": row[5],
                    "avg_passing_yards": float(row[6]) if row[6] else 0.0,
                    "avg_rushing_yards": float(row[7]) if row[7] else 0.0,
                    "avg_receiving_yards": float(row[8]) if row[8] else 0.0,
                    "avg_tackles": float(row[9]) if row[9] else 0.0,
                })
            
            return positions
        except Exception as e:
            logger.warning(f"Error getting position statistics: {e}")
            return []

    async def _get_college_statistics(self) -> List[Dict[str, Any]]:
        """Get CFR statistics breakdown by college (top 20)."""
        try:
            result = await self.db.execute(
                text("""
                    SELECT 
                        college,
                        COUNT(*) as total_prospects,
                        COUNT(DISTINCT position) as position_count,
                        ROUND(AVG(CAST(passing_yards AS NUMERIC)), 2) as avg_passing,
                        ROUND(AVG(CAST(rushing_yards AS NUMERIC)), 2) as avg_rushing,
                        ROUND(AVG(CAST(receiving_yards AS NUMERIC)), 2) as avg_receiving
                    FROM prospect_college_stats
                    WHERE season >= 2020 AND college IS NOT NULL
                    GROUP BY college
                    ORDER BY total_prospects DESC
                    LIMIT 20
                """)
            )
            
            colleges = []
            for row in result.fetchall():
                colleges.append({
                    "college": row[0],
                    "total_prospects": row[1],
                    "position_count": row[2],
                    "avg_passing_yards": float(row[3]) if row[3] else 0.0,
                    "avg_rushing_yards": float(row[4]) if row[4] else 0.0,
                    "avg_receiving_yards": float(row[5]) if row[5] else 0.0,
                })
            
            return colleges
        except Exception as e:
            logger.warning(f"Error getting college statistics: {e}")
            return []

    async def _get_30day_trends(self) -> List[Dict[str, Any]]:
        """Get 30-day quality metrics trends."""
        try:
            # For now, calculate daily for last 30 days
            trends = []
            base_date = datetime.utcnow().date()
            
            for i in range(30):
                day = base_date - timedelta(days=i)
                
                # Count records loaded on/before this day
                result = await self.db.execute(
                    text("""
                        SELECT COUNT(*) as count 
                        FROM prospect_college_stats 
                        WHERE DATE(created_at) <= :date
                        AND season >= 2020
                    """),
                    {"date": day}
                )
                
                count = result.scalar() or 0
                trends.append({
                    "date": day.isoformat(),
                    "total_records": count,
                })
            
            return list(reversed(trends))
        except Exception as e:
            logger.warning(f"Error getting 30-day trends: {e}")
            return []


class CFRQualityAlerts:
    """Generate quality alerts based on metrics."""

    # Default thresholds
    MIN_MATCH_RATE = 85.0  # 85% minimum match rate
    MIN_LOAD_SUCCESS_RATE = 90.0  # 90% minimum load success rate
    MIN_QUALITY_SCORE = 80.0  # 80% minimum overall quality score
    MAX_ERROR_COUNT = 5  # Maximum parse errors

    @staticmethod
    async def check_quality_thresholds(
        metrics: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Check if metrics exceed quality thresholds.
        
        Args:
            metrics: Quality metrics from CFRAnalyticsCalculator
            
        Returns:
            Dict with alerts and status
        """
        alerts = []
        
        if "error" in metrics:
            return {
                "status": "error",
                "alerts": [f"Could not calculate metrics: {metrics['error']}"],
            }
        
        # Check match rate
        if metrics.get("match_rate", 0) < CFRQualityAlerts.MIN_MATCH_RATE:
            alerts.append(
                f"⚠️ Low match rate: {metrics['match_rate']}% "
                f"(threshold: {CFRQualityAlerts.MIN_MATCH_RATE}%)"
            )
        
        # Check load success rate
        if metrics.get("load_success_rate", 0) < CFRQualityAlerts.MIN_LOAD_SUCCESS_RATE:
            alerts.append(
                f"⚠️ Low load success rate: {metrics['load_success_rate']}% "
                f"(threshold: {CFRQualityAlerts.MIN_LOAD_SUCCESS_RATE}%)"
            )
        
        # Check overall quality score
        if metrics.get("overall_quality_score", 0) < CFRQualityAlerts.MIN_QUALITY_SCORE:
            alerts.append(
                f"🔴 Critical quality issue: {metrics['overall_quality_score']}% "
                f"(threshold: {CFRQualityAlerts.MIN_QUALITY_SCORE}%)"
            )
        
        # Check error count
        if metrics.get("parse_error_count", 0) > CFRQualityAlerts.MAX_ERROR_COUNT:
            alerts.append(
                f"⚠️ High parse error count: {metrics['parse_error_count']} "
                f"(threshold: {CFRQualityAlerts.MAX_ERROR_COUNT})"
            )
        
        status = "critical" if any("🔴" in a for a in alerts) else "warning" if alerts else "ok"
        
        return {
            "status": status,
            "alerts": alerts,
            "timestamp": datetime.utcnow().isoformat(),
            "quality_score": metrics.get("overall_quality_score", 0),
        }
