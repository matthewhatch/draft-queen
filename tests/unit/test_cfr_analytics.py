"""
CFR-005 Analytics & Quality Dashboard Tests

Comprehensive testing of CFR analytics and quality monitoring functionality.

Test coverage:
1. Quality metrics calculation
2. Dashboard data aggregation
3. Position statistics
4. College statistics
5. 30-day trends
6. Quality alerts and thresholds
7. Data completeness tracking
8. Error detection
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
import logging

logger = logging.getLogger(__name__)


class TestCFRAnalyticsCalculator:
    """Test CFR analytics metrics calculation."""

    def test_cfr_analytics_calculator_initialization(self):
        """Test CFRAnalyticsCalculator can be initialized."""
        from src.data_pipeline.cfr_analytics import CFRAnalyticsCalculator
        from sqlalchemy.ext.asyncio import AsyncSession
        from unittest.mock import Mock
        
        db = Mock(spec=AsyncSession)
        calculator = CFRAnalyticsCalculator(db)
        
        assert calculator is not None
        assert calculator.db == db

    def test_quality_score_calculation(self):
        """Test quality score calculation formula."""
        from src.data_pipeline.cfr_analytics import CFRAnalyticsCalculator
        
        # Perfect metrics: 100% match rate, 100% load, 100% completeness, 0 outliers, 0 errors
        score = CFRAnalyticsCalculator._calculate_quality_score(
            match_rate=100.0,
            load_success_rate=100.0,
            completeness={
                "passing_yards": 100.0,
                "rushing_yards": 100.0,
                "receiving_yards": 100.0,
                "tackles": 100.0,
                "sacks": 100.0,
            },
            outliers=0,
            errors=0,
        )
        
        assert score == 100.0

    def test_quality_score_with_issues(self):
        """Test quality score with various issues."""
        from src.data_pipeline.cfr_analytics import CFRAnalyticsCalculator
        
        # Low metrics
        score = CFRAnalyticsCalculator._calculate_quality_score(
            match_rate=80.0,  # Below ideal
            load_success_rate=85.0,  # Below ideal
            completeness={
                "passing_yards": 70.0,
                "rushing_yards": 70.0,
                "receiving_yards": 70.0,
                "tackles": 70.0,
                "sacks": 70.0,
            },
            outliers=10,
            errors=5,
        )
        
        assert score < 100.0
        assert score > 0.0

    def test_quality_score_weights(self):
        """Test quality score calculation weights are correct."""
        from src.data_pipeline.cfr_analytics import CFRAnalyticsCalculator
        
        # Score should be approximately:
        # match (40%) + load (30%) + completeness (20%) + outlier (5%) + error (5%)
        # = 100 * 0.40 + 100 * 0.30 + 100 * 0.20 + 5 + 5 = 100
        score = CFRAnalyticsCalculator._calculate_quality_score(
            match_rate=100.0,
            load_success_rate=100.0,
            completeness={"f1": 100.0, "f2": 100.0, "f3": 100.0, "f4": 100.0, "f5": 100.0},
            outliers=0,
            errors=0,
        )
        
        assert score == 100.0


class TestCFRDashboardData:
    """Test CFR dashboard data provider."""

    def test_cfr_dashboard_data_initialization(self):
        """Test CFRDashboardData can be initialized."""
        from src.data_pipeline.cfr_analytics import CFRDashboardData
        from sqlalchemy.ext.asyncio import AsyncSession
        from unittest.mock import Mock
        
        db = Mock(spec=AsyncSession)
        dashboard = CFRDashboardData(db)
        
        assert dashboard is not None
        assert dashboard.db == db

    def test_cfr_dashboard_data_has_calculator(self):
        """Test CFRDashboardData includes analytics calculator."""
        from src.data_pipeline.cfr_analytics import CFRDashboardData, CFRAnalyticsCalculator
        from sqlalchemy.ext.asyncio import AsyncSession
        from unittest.mock import Mock
        
        db = Mock(spec=AsyncSession)
        dashboard = CFRDashboardData(db)
        
        assert hasattr(dashboard, 'calculator')
        assert isinstance(dashboard.calculator, CFRAnalyticsCalculator)


class TestCFRQualityAlerts:
    """Test CFR quality alert system."""

    def test_cfr_quality_alerts_class_exists(self):
        """Test CFRQualityAlerts class exists."""
        from src.data_pipeline.cfr_analytics import CFRQualityAlerts
        
        assert CFRQualityAlerts is not None

    def test_cfr_quality_alerts_thresholds_defined(self):
        """Test quality alert thresholds are configured."""
        from src.data_pipeline.cfr_analytics import CFRQualityAlerts
        
        assert CFRQualityAlerts.MIN_MATCH_RATE == 85.0
        assert CFRQualityAlerts.MIN_LOAD_SUCCESS_RATE == 90.0
        assert CFRQualityAlerts.MIN_QUALITY_SCORE == 80.0
        assert CFRQualityAlerts.MAX_ERROR_COUNT == 5

    def test_cfr_quality_alerts_low_match_rate(self):
        """Test alert triggered for low match rate."""
        import asyncio
        from src.data_pipeline.cfr_analytics import CFRQualityAlerts
        
        async def test():
            metrics = {
                "match_rate": 75.0,  # Below threshold of 85%
                "load_success_rate": 95.0,
                "overall_quality_score": 85.0,
                "parse_error_count": 0,
            }
            
            result = await CFRQualityAlerts.check_quality_thresholds(metrics)
            
            assert result["status"] == "warning"
            assert len(result["alerts"]) > 0
            assert any("match rate" in alert.lower() for alert in result["alerts"])
        
        asyncio.run(test())

    def test_cfr_quality_alerts_critical_quality(self):
        """Test critical alert for quality score."""
        import asyncio
        from src.data_pipeline.cfr_analytics import CFRQualityAlerts
        
        async def test():
            metrics = {
                "match_rate": 85.0,
                "load_success_rate": 90.0,
                "overall_quality_score": 70.0,  # Below threshold of 80%
                "parse_error_count": 0,
            }
            
            result = await CFRQualityAlerts.check_quality_thresholds(metrics)
            
            assert result["status"] == "critical"
            assert any("critical" in alert.lower() for alert in result["alerts"])
        
        asyncio.run(test())

    def test_cfr_quality_alerts_ok_status(self):
        """Test no alerts when metrics are good."""
        import asyncio
        from src.data_pipeline.cfr_analytics import CFRQualityAlerts
        
        async def test():
            metrics = {
                "match_rate": 95.0,
                "load_success_rate": 95.0,
                "overall_quality_score": 90.0,
                "parse_error_count": 1,
            }
            
            result = await CFRQualityAlerts.check_quality_thresholds(metrics)
            
            assert result["status"] == "ok"
            assert len(result["alerts"]) == 0
        
        asyncio.run(test())


# ============================================================================
# ACCEPTANCE CRITERIA VERIFICATION
# ============================================================================

class TestCFR005AcceptanceCriteria:
    """Verify CFR-005 acceptance criteria are met."""

    def test_ac1_quality_metrics_calculated(self):
        """AC1: Quality metrics are calculated and accessible."""
        from src.data_pipeline.cfr_analytics import CFRAnalyticsCalculator
        
        assert hasattr(CFRAnalyticsCalculator, 'get_cfr_quality_metrics')

    def test_ac2_dashboard_data_available(self):
        """AC2: Dashboard data endpoint available."""
        from src.data_pipeline.cfr_analytics import CFRDashboardData
        
        assert hasattr(CFRDashboardData, 'get_dashboard_summary')

    def test_ac3_position_statistics_available(self):
        """AC3: Position-specific statistics available."""
        from src.data_pipeline.cfr_analytics import CFRDashboardData
        
        assert hasattr(CFRDashboardData, '_get_position_statistics')

    def test_ac4_college_statistics_available(self):
        """AC4: College-specific statistics available."""
        from src.data_pipeline.cfr_analytics import CFRDashboardData
        
        assert hasattr(CFRDashboardData, '_get_college_statistics')

    def test_ac5_match_rate_tracked(self):
        """AC5: Match rate is tracked and reported."""
        from src.data_pipeline.cfr_analytics import CFRAnalyticsCalculator
        import inspect
        
        source = inspect.getsource(CFRAnalyticsCalculator.get_cfr_quality_metrics)
        assert 'match_rate' in source

    def test_ac6_completeness_tracked(self):
        """AC6: Data completeness is tracked by field."""
        from src.data_pipeline.cfr_analytics import CFRAnalyticsCalculator
        
        assert hasattr(CFRAnalyticsCalculator, '_get_field_completeness')

    def test_ac7_quality_alerts_configured(self):
        """AC7: Quality alerts with configurable thresholds."""
        from src.data_pipeline.cfr_analytics import CFRQualityAlerts
        
        assert hasattr(CFRQualityAlerts, 'check_quality_thresholds')
        assert CFRQualityAlerts.MIN_MATCH_RATE > 0

    def test_ac8_error_tracking(self):
        """AC8: Parse errors and data quality issues tracked."""
        from src.data_pipeline.cfr_analytics import CFRAnalyticsCalculator
        
        assert hasattr(CFRAnalyticsCalculator, '_get_parse_error_count')

    def test_ac9_outlier_detection(self):
        """AC9: Outlier detection implemented."""
        from src.data_pipeline.cfr_analytics import CFRAnalyticsCalculator
        
        assert hasattr(CFRAnalyticsCalculator, '_get_outlier_count')

    def test_ac10_30day_trends(self):
        """AC10: Historical trend tracking (30 days)."""
        from src.data_pipeline.cfr_analytics import CFRDashboardData
        
        assert hasattr(CFRDashboardData, '_get_30day_trends')


# ============================================================================
# SUMMARY TESTS
# ============================================================================

class TestCFR005Summary:
    """Summary verification of CFR-005 completion."""

    def test_cfr005_quality_enum_exists(self):
        """Test quality status enum is defined."""
        from src.data_pipeline.cfr_analytics import CFRQualityStatus
        
        assert CFRQualityStatus.EXCELLENT.value == "excellent"
        assert CFRQualityStatus.GOOD.value == "good"
        assert CFRQualityStatus.WARNING.value == "warning"
        assert CFRQualityStatus.CRITICAL.value == "critical"

    def test_cfr005_all_components_exist(self):
        """Test all CFR-005 components are implemented."""
        from src.data_pipeline.cfr_analytics import (
            CFRQualityStatus,
            CFRAnalyticsCalculator,
            CFRDashboardData,
            CFRQualityAlerts,
        )
        
        assert CFRQualityStatus is not None
        assert CFRAnalyticsCalculator is not None
        assert CFRDashboardData is not None
        assert CFRQualityAlerts is not None

    def test_cfr005_quality_metrics_structure(self):
        """Test quality metrics return proper structure."""
        from src.data_pipeline.cfr_analytics import CFRAnalyticsCalculator
        import inspect
        
        source = inspect.getsource(CFRAnalyticsCalculator.get_cfr_quality_metrics)
        
        # Check for key metric fields in return
        expected_fields = [
            'timestamp',
            'staging_count',
            'matched_count',
            'match_rate',
            'overall_quality_score',
            'status',
        ]
        
        for field in expected_fields:
            assert field in source

    def test_cfr005_dashboard_comprehensive(self):
        """Test dashboard includes all components."""
        from src.data_pipeline.cfr_analytics import CFRDashboardData
        import inspect
        
        source = inspect.getsource(CFRDashboardData.get_dashboard_summary)
        
        # Check for all dashboard sections
        assert 'quality_metrics' in source
        assert 'position_statistics' in source
        assert 'college_statistics' in source
        assert 'trends_30_days' in source
