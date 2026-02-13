"""Grade-specific quality validation and outlier detection.

Implements multi-source grade validation, outlier detection using z-score,
and suspicious pattern flagging for prospect grades.

US-044: Enhanced Data Quality for Multi-Source Grades
"""

import logging
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class GradeOutlierSeverity(Enum):
    """Severity of outlier detection."""
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class GradeValidationResult:
    """Result of grade validation check."""
    prospect_id: str
    grade_source: str
    position: str
    is_valid: bool
    violations: List[str] = field(default_factory=list)
    outliers: List[Dict[str, Any]] = field(default_factory=list)
    grade_value: Optional[float] = None
    prior_grade: Optional[float] = None
    grade_change: Optional[float] = None
    change_percentage: Optional[float] = None
    std_dev_from_mean: Optional[float] = None
    severity: GradeOutlierSeverity = GradeOutlierSeverity.NORMAL
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "prospect_id": self.prospect_id,
            "grade_source": self.grade_source,
            "position": self.position,
            "is_valid": self.is_valid,
            "violations": self.violations,
            "outliers": self.outliers,
            "grade_value": self.grade_value,
            "prior_grade": self.prior_grade,
            "grade_change": self.grade_change,
            "change_percentage": self.change_percentage,
            "std_dev_from_mean": self.std_dev_from_mean,
            "severity": self.severity.value,
        }


class GradeValidator:
    """Validates prospect grades and detects outliers."""
    
    def __init__(self, session: Session):
        """Initialize validator with database session.
        
        Args:
            session: SQLAlchemy Session for database queries
        """
        self.session = session
        self.stats = {
            "total_validated": 0,
            "valid": 0,
            "invalid": 0,
            "outliers": 0,
        }
    
    def validate_grade_range(
        self,
        prospect_id: str,
        grade: float,
        grade_source: str,
    ) -> GradeValidationResult:
        """Validate that grade is within acceptable range for source.
        
        Args:
            prospect_id: Prospect ID
            grade: Grade value to validate
            grade_source: Source of grade (pff, espn, nfl, yahoo)
            
        Returns:
            GradeValidationResult with validation status
        """
        result = GradeValidationResult(
            prospect_id=prospect_id,
            grade_source=grade_source,
            position="",
            is_valid=True,
            grade_value=grade,
        )
        
        # Source-specific ranges
        valid_ranges = {
            "pff": (0, 100),           # PFF: 0-100 scale
            "espn": (0, 100),          # ESPN: 0-100 scale
            "nfl": (5.0, 10.0),        # NFL.com: 5.0-10.0 scale
            "yahoo": (0, 100),         # Yahoo: 0-100 scale
        }
        
        if grade_source.lower() not in valid_ranges:
            result.violations.append(f"Unknown grade source: {grade_source}")
            result.is_valid = False
            return result
        
        min_val, max_val = valid_ranges[grade_source.lower()]
        
        if not (min_val <= grade <= max_val):
            result.violations.append(
                f"{grade_source} grade {grade} outside valid range ({min_val}, {max_val})"
            )
            result.is_valid = False
        
        return result
    
    def detect_outliers_zscore(
        self,
        prospect_id: str,
        grade_value: float,
        position: str,
        grade_source: str,
        position_grades: List[float],
        threshold_std_dev: float = 2.0,
    ) -> GradeValidationResult:
        """Detect outliers using z-score method (2 std dev from mean).
        
        Args:
            prospect_id: Prospect ID
            grade_value: Grade to check
            position: Player position
            grade_source: Source of grade
            position_grades: List of all grades for position group
            threshold_std_dev: How many std devs = outlier (default: 2.0)
            
        Returns:
            GradeValidationResult with outlier detection
        """
        result = GradeValidationResult(
            prospect_id=prospect_id,
            grade_source=grade_source,
            position=position,
            is_valid=True,
            grade_value=grade_value,
        )
        
        if not position_grades or len(position_grades) < 3:
            logger.warning(
                f"Insufficient data for outlier detection: "
                f"position={position}, count={len(position_grades)}"
            )
            return result
        
        try:
            mean = statistics.mean(position_grades)
            stdev = statistics.stdev(position_grades) if len(position_grades) > 1 else 0
            
            if stdev == 0:
                # All grades identical, no outliers possible
                return result
            
            # Calculate z-score
            z_score = (grade_value - mean) / stdev
            std_dev_from_mean = abs(z_score)
            
            result.std_dev_from_mean = round(std_dev_from_mean, 2)
            
            # Flag as outlier if beyond threshold
            if std_dev_from_mean >= threshold_std_dev:
                result.outliers.append({
                    "type": "z_score_outlier",
                    "z_score": round(z_score, 2),
                    "std_dev_from_mean": round(std_dev_from_mean, 2),
                    "position_mean": round(mean, 2),
                    "position_stdev": round(stdev, 2),
                    "threshold": threshold_std_dev,
                })
                
                # Severity based on how extreme
                if std_dev_from_mean >= 3.0:
                    result.severity = GradeOutlierSeverity.CRITICAL
                else:
                    result.severity = GradeOutlierSeverity.WARNING
                    
                self.stats["outliers"] += 1
                logger.warning(
                    f"Outlier detected: prospect={prospect_id}, position={position}, "
                    f"grade={grade_value}, z_score={z_score:.2f}, threshold={threshold_std_dev}"
                )
        
        except Exception as e:
            logger.error(f"Error calculating outlier z-score: {e}")
            result.violations.append(f"Outlier detection failed: {str(e)}")
        
        return result
    
    def detect_grade_change(
        self,
        prospect_id: str,
        current_grade: float,
        prior_grade: Optional[float],
        grade_source: str,
        position: str,
        change_threshold_percentage: float = 20.0,  # 20% change = suspicious
    ) -> GradeValidationResult:
        """Detect suspicious grade changes day-over-day.
        
        Args:
            prospect_id: Prospect ID
            current_grade: Current grade value
            prior_grade: Previous grade value (or None if new)
            grade_source: Source of grade
            position: Player position
            change_threshold_percentage: % change to flag as suspicious
            
        Returns:
            GradeValidationResult with change detection
        """
        result = GradeValidationResult(
            prospect_id=prospect_id,
            grade_source=grade_source,
            position=position,
            is_valid=True,
            grade_value=current_grade,
            prior_grade=prior_grade,
        )
        
        if prior_grade is None:
            # New prospect or new source, no change to detect
            return result
        
        grade_change = current_grade - prior_grade
        result.grade_change = round(grade_change, 2)
        
        # Calculate percentage change
        if prior_grade != 0:
            change_pct = (grade_change / abs(prior_grade)) * 100
        else:
            change_pct = 0 if grade_change == 0 else 100
        
        result.change_percentage = round(change_pct, 1)
        
        # Flag if change exceeds threshold
        if abs(change_pct) >= change_threshold_percentage:
            result.outliers.append({
                "type": "suspicious_grade_change",
                "prior_grade": prior_grade,
                "current_grade": current_grade,
                "change": grade_change,
                "change_percentage": change_pct,
                "threshold_percentage": change_threshold_percentage,
            })
            
            # Severity based on magnitude
            if abs(change_pct) >= 50:  # 50% change = critical
                result.severity = GradeOutlierSeverity.CRITICAL
            else:
                result.severity = GradeOutlierSeverity.WARNING
            
            logger.warning(
                f"Suspicious grade change: prospect={prospect_id}, source={grade_source}, "
                f"prior={prior_grade}, current={current_grade}, change={change_pct:.1f}%"
            )
        
        return result
    
    def validate_grade_completeness(
        self,
        prospect_id: str,
        available_sources: List[str],
        required_sources: Optional[List[str]] = None,
    ) -> GradeValidationResult:
        """Validate that prospect has sufficient grade sources.
        
        Args:
            prospect_id: Prospect ID
            available_sources: List of sources with grades for prospect
            required_sources: Minimum sources required (or None = at least 1)
            
        Returns:
            GradeValidationResult with completeness check
        """
        result = GradeValidationResult(
            prospect_id=prospect_id,
            grade_source="multi-source",
            position="",
            is_valid=True,
        )
        
        if required_sources is None:
            required_sources = ["pff"]  # At least PFF required
        
        missing = set(required_sources) - set(available_sources)
        
        if missing:
            result.violations.append(
                f"Missing grades from required sources: {', '.join(missing)}"
            )
            result.is_valid = False
            result.severity = GradeOutlierSeverity.WARNING
        
        if len(available_sources) == 0:
            result.violations.append("No grade sources available for prospect")
            result.is_valid = False
            result.severity = GradeOutlierSeverity.CRITICAL
        
        return result
    
    def validate_prospect_grades(
        self,
        prospect_id: str,
        position: str,
        grades_dict: Dict[str, float],  # {"pff": 92, "espn": 85, ...}
        position_grades: Dict[str, List[float]],  # {"pff": [88, 90, 92, ...], ...}
        prior_grades: Optional[Dict[str, float]] = None,
    ) -> GradeValidationResult:
        """Comprehensive grade validation for a prospect.
        
        Args:
            prospect_id: Prospect ID
            position: Player position
            grades_dict: Current grades by source
            position_grades: All grades for position group by source
            prior_grades: Previous grades by source (for change detection)
            
        Returns:
            GradeValidationResult with all validations
        """
        result = GradeValidationResult(
            prospect_id=prospect_id,
            grade_source="multi-source",
            position=position,
            is_valid=True,
        )
        
        self.stats["total_validated"] += 1
        all_valid = True
        
        # Check each source
        for source, grade_value in grades_dict.items():
            # 1. Range validation
            range_result = self.validate_grade_range(
                prospect_id, grade_value, source
            )
            if not range_result.is_valid:
                all_valid = False
                result.violations.extend(range_result.violations)
                continue
            
            # 2. Outlier detection (z-score)
            if source in position_grades:
                outlier_result = self.detect_outliers_zscore(
                    prospect_id, grade_value, position, source,
                    position_grades[source]
                )
                result.outliers.extend(outlier_result.outliers)
                if outlier_result.severity == GradeOutlierSeverity.CRITICAL:
                    result.severity = GradeOutlierSeverity.CRITICAL
            
            # 3. Grade change detection
            if prior_grades and source in prior_grades:
                change_result = self.detect_grade_change(
                    prospect_id, grade_value, prior_grades.get(source),
                    source, position
                )
                result.outliers.extend(change_result.outliers)
                result.grade_change = change_result.grade_change
                result.change_percentage = change_result.change_percentage
        
        # 4. Completeness check
        completeness_result = self.validate_grade_completeness(
            prospect_id, list(grades_dict.keys())
        )
        if not completeness_result.is_valid:
            all_valid = False
            result.violations.extend(completeness_result.violations)
        
        result.is_valid = all_valid
        
        if all_valid:
            self.stats["valid"] += 1
        else:
            self.stats["invalid"] += 1
        
        return result
    
    def get_stats(self) -> Dict[str, int]:
        """Get validation statistics."""
        return self.stats.copy()
