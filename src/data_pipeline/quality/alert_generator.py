"""Alert generation engine for quality metrics.

Analyzes quality metrics against configurable thresholds and generates
alerts for data quality issues.

US-044: Enhanced Data Quality for Multi-Source Grades - Phase 4
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertType(Enum):
    """Types of quality alerts."""
    LOW_COVERAGE = "low_coverage"
    LOW_VALIDATION = "low_validation"
    HIGH_OUTLIERS = "high_outliers"
    LOW_OVERALL_SCORE = "low_overall_score"
    GRADE_FRESHNESS = "grade_freshness"
    SOURCE_MISSING = "source_missing"


class AlertThreshold:
    """Alert threshold configuration."""
    
    def __init__(self):
        """Initialize with default thresholds."""
        # Quality score thresholds
        self.quality_score_normal = 85.0      # >= this is normal
        self.quality_score_warning = 75.0     # 75-85 is warning
        self.quality_score_critical = 70.0    # < this is critical
        
        # Component thresholds
        self.coverage_warning = 80.0          # Coverage < 80% is warning
        self.coverage_critical = 70.0         # Coverage < 70% is critical
        self.validation_warning = 85.0        # Validation < 85% is warning
        self.validation_critical = 75.0       # Validation < 75% is critical
        self.outlier_warning = 5.0            # Outliers > 5% is warning
        self.outlier_critical = 10.0          # Outliers > 10% is critical
        
        # Freshness thresholds (days)
        self.grade_freshness_warning = 14     # No grades for 14+ days is warning
        self.grade_freshness_critical = 30    # No grades for 30+ days is critical


class AlertGenerator:
    """Generate quality alerts from metrics.
    
    Evaluates quality metrics against thresholds and creates alerts
    for data quality issues.
    """
    
    def __init__(self, thresholds: Optional[AlertThreshold] = None):
        """Initialize alert generator.
        
        Args:
            thresholds: Custom AlertThreshold configuration (uses defaults if None)
        """
        self.thresholds = thresholds or AlertThreshold()
    
    def generate_alerts(self, 
                       metric: Dict,
                       position: Optional[str] = None,
                       source: Optional[str] = None) -> List[Dict]:
        """Generate alerts from a quality metric.
        
        Args:
            metric: Quality metric dictionary with keys:
                - coverage_percentage: float (0-100)
                - validation_percentage: float (0-100)
                - outlier_percentage: float (0-100)
                - quality_score: float (0-100)
                - metric_date: datetime
                - position: Optional[str]
                - grade_source: Optional[str]
            position: Position context for alert generation
            source: Grade source context for alert generation
        
        Returns:
            List of alert dictionaries:
            [
                {
                    'alert_type': 'low_coverage',
                    'severity': 'warning',
                    'message': 'Coverage for QB from pff is 75.0% (threshold: 80.0%)',
                    'metric_value': 75.0,
                    'threshold_value': 80.0,
                    'position': 'QB',
                    'grade_source': 'pff',
                    'quality_score': 82.5,
                    'generated_at': datetime(2026, 2, 14, 15, 30, 0)
                },
                ...
            ]
        """
        alerts = []
        
        # Extract metric values
        coverage = metric.get('coverage_percentage', 0.0)
        validation = metric.get('validation_percentage', 0.0)
        outliers = metric.get('outlier_percentage', 0.0)
        quality_score = metric.get('quality_score', 0.0)
        metric_date = metric.get('metric_date', datetime.utcnow())
        position = position or metric.get('position')
        source = source or metric.get('grade_source')
        
        # Check coverage
        coverage_alerts = self._check_coverage(coverage, quality_score, position, source, metric_date)
        alerts.extend(coverage_alerts)
        
        # Check validation
        validation_alerts = self._check_validation(validation, quality_score, position, source, metric_date)
        alerts.extend(validation_alerts)
        
        # Check outliers
        outlier_alerts = self._check_outliers(outliers, quality_score, position, source, metric_date)
        alerts.extend(outlier_alerts)
        
        # Check overall quality score
        score_alerts = self._check_quality_score(quality_score, position, source, metric_date)
        alerts.extend(score_alerts)
        
        logger.info(f"Generated {len(alerts)} alerts for {position}/{source}")
        return alerts
    
    def _check_coverage(self,
                       coverage: float,
                       quality_score: float,
                       position: Optional[str],
                       source: Optional[str],
                       metric_date: datetime) -> List[Dict]:
        """Check coverage against thresholds.
        
        Args:
            coverage: Coverage percentage (0-100)
            quality_score: Overall quality score
            position: Position context
            source: Grade source context
            metric_date: Metric generation date
        
        Returns:
            List of coverage-related alerts (0-1 alert)
        """
        alerts = []
        
        if coverage < self.thresholds.coverage_critical:
            # Critical alert
            severity = AlertSeverity.CRITICAL.value
            message = (f"Coverage for {position} from {source} is {coverage:.1f}% "
                      f"(critical threshold: {self.thresholds.coverage_critical:.1f}%)")
            alerts.append({
                'alert_type': AlertType.LOW_COVERAGE.value,
                'severity': severity,
                'message': message,
                'metric_value': coverage,
                'threshold_value': self.thresholds.coverage_critical,
                'position': position,
                'grade_source': source,
                'quality_score': quality_score,
                'generated_at': metric_date,
            })
        elif coverage < self.thresholds.coverage_warning:
            # Warning alert
            severity = AlertSeverity.WARNING.value
            message = (f"Coverage for {position} from {source} is {coverage:.1f}% "
                      f"(warning threshold: {self.thresholds.coverage_warning:.1f}%)")
            alerts.append({
                'alert_type': AlertType.LOW_COVERAGE.value,
                'severity': severity,
                'message': message,
                'metric_value': coverage,
                'threshold_value': self.thresholds.coverage_warning,
                'position': position,
                'grade_source': source,
                'quality_score': quality_score,
                'generated_at': metric_date,
            })
        
        return alerts
    
    def _check_validation(self,
                         validation: float,
                         quality_score: float,
                         position: Optional[str],
                         source: Optional[str],
                         metric_date: datetime) -> List[Dict]:
        """Check validation against thresholds.
        
        Args:
            validation: Validation percentage (0-100)
            quality_score: Overall quality score
            position: Position context
            source: Grade source context
            metric_date: Metric generation date
        
        Returns:
            List of validation-related alerts (0-1 alert)
        """
        alerts = []
        
        if validation < self.thresholds.validation_critical:
            # Critical alert
            severity = AlertSeverity.CRITICAL.value
            message = (f"Validation for {position} from {source} is {validation:.1f}% "
                      f"(critical threshold: {self.thresholds.validation_critical:.1f}%)")
            alerts.append({
                'alert_type': AlertType.LOW_VALIDATION.value,
                'severity': severity,
                'message': message,
                'metric_value': validation,
                'threshold_value': self.thresholds.validation_critical,
                'position': position,
                'grade_source': source,
                'quality_score': quality_score,
                'generated_at': metric_date,
            })
        elif validation < self.thresholds.validation_warning:
            # Warning alert
            severity = AlertSeverity.WARNING.value
            message = (f"Validation for {position} from {source} is {validation:.1f}% "
                      f"(warning threshold: {self.thresholds.validation_warning:.1f}%)")
            alerts.append({
                'alert_type': AlertType.LOW_VALIDATION.value,
                'severity': severity,
                'message': message,
                'metric_value': validation,
                'threshold_value': self.thresholds.validation_warning,
                'position': position,
                'grade_source': source,
                'quality_score': quality_score,
                'generated_at': metric_date,
            })
        
        return alerts
    
    def _check_outliers(self,
                       outliers: float,
                       quality_score: float,
                       position: Optional[str],
                       source: Optional[str],
                       metric_date: datetime) -> List[Dict]:
        """Check outliers against thresholds.
        
        Args:
            outliers: Outlier percentage (0-100)
            quality_score: Overall quality score
            position: Position context
            source: Grade source context
            metric_date: Metric generation date
        
        Returns:
            List of outlier-related alerts (0-1 alert)
        """
        alerts = []
        
        if outliers > self.thresholds.outlier_critical:
            # Critical alert
            severity = AlertSeverity.CRITICAL.value
            message = (f"Outliers for {position} from {source} is {outliers:.1f}% "
                      f"(critical threshold: {self.thresholds.outlier_critical:.1f}%)")
            alerts.append({
                'alert_type': AlertType.HIGH_OUTLIERS.value,
                'severity': severity,
                'message': message,
                'metric_value': outliers,
                'threshold_value': self.thresholds.outlier_critical,
                'position': position,
                'grade_source': source,
                'quality_score': quality_score,
                'generated_at': metric_date,
            })
        elif outliers > self.thresholds.outlier_warning:
            # Warning alert
            severity = AlertSeverity.WARNING.value
            message = (f"Outliers for {position} from {source} is {outliers:.1f}% "
                      f"(warning threshold: {self.thresholds.outlier_warning:.1f}%)")
            alerts.append({
                'alert_type': AlertType.HIGH_OUTLIERS.value,
                'severity': severity,
                'message': message,
                'metric_value': outliers,
                'threshold_value': self.thresholds.outlier_warning,
                'position': position,
                'grade_source': source,
                'quality_score': quality_score,
                'generated_at': metric_date,
            })
        
        return alerts
    
    def _check_quality_score(self,
                            quality_score: float,
                            position: Optional[str],
                            source: Optional[str],
                            metric_date: datetime) -> List[Dict]:
        """Check overall quality score against thresholds.
        
        Args:
            quality_score: Overall quality score (0-100)
            position: Position context
            source: Grade source context
            metric_date: Metric generation date
        
        Returns:
            List of quality score alerts (0-1 alert)
        """
        alerts = []
        
        if quality_score < self.thresholds.quality_score_critical:
            # Critical alert
            severity = AlertSeverity.CRITICAL.value
            message = (f"Quality score for {position} from {source} is {quality_score:.1f} "
                      f"(critical threshold: {self.thresholds.quality_score_critical:.1f})")
            alerts.append({
                'alert_type': AlertType.LOW_OVERALL_SCORE.value,
                'severity': severity,
                'message': message,
                'metric_value': quality_score,
                'threshold_value': self.thresholds.quality_score_critical,
                'position': position,
                'grade_source': source,
                'quality_score': quality_score,
                'generated_at': metric_date,
            })
        elif quality_score < self.thresholds.quality_score_warning:
            # Warning alert
            severity = AlertSeverity.WARNING.value
            message = (f"Quality score for {position} from {source} is {quality_score:.1f} "
                      f"(warning threshold: {self.thresholds.quality_score_warning:.1f})")
            alerts.append({
                'alert_type': AlertType.LOW_OVERALL_SCORE.value,
                'severity': severity,
                'message': message,
                'metric_value': quality_score,
                'threshold_value': self.thresholds.quality_score_warning,
                'position': position,
                'grade_source': source,
                'quality_score': quality_score,
                'generated_at': metric_date,
            })
        
        return alerts
    
    def get_severity_level(self, severity: str) -> int:
        """Get numeric severity level for sorting.
        
        Args:
            severity: Severity string ('info', 'warning', 'critical')
        
        Returns:
            Numeric level (0=info, 1=warning, 2=critical)
        """
        severity_levels = {
            AlertSeverity.INFO.value: 0,
            AlertSeverity.WARNING.value: 1,
            AlertSeverity.CRITICAL.value: 2,
        }
        return severity_levels.get(severity, 0)
    
    def get_priority_score(self, alert: Dict) -> float:
        """Calculate priority score for alert (higher = more urgent).
        
        Args:
            alert: Alert dictionary with severity and metric_value
        
        Returns:
            Priority score (0-100)
        """
        severity = alert.get('severity', AlertSeverity.INFO.value)
        metric_value = alert.get('metric_value', 0)
        threshold = alert.get('threshold_value', 100)
        
        # Severity multiplier
        severity_multipliers = {
            AlertSeverity.INFO.value: 0.5,
            AlertSeverity.WARNING.value: 1.5,
            AlertSeverity.CRITICAL.value: 2.5,
        }
        severity_mult = severity_multipliers.get(severity, 1.0)
        
        # Deviation from threshold (how far below warning threshold)
        if threshold > 0:
            deviation = max(0, threshold - metric_value)
            deviation_ratio = min(1.0, deviation / threshold)
        else:
            deviation_ratio = 0
        
        # Priority = severity_mult × deviation_ratio × 100
        priority = severity_mult * deviation_ratio * 100
        return min(100, priority)
