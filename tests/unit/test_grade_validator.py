"""Unit tests for grade validator - direct imports to avoid __init__.py dependencies.

Tests for US-044: Enhanced Data Quality for Multi-Source Grades
"""

import pytest
from datetime import datetime
from unittest.mock import Mock
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

# Import directly from modules, not packages
import importlib.util

# Load grade_validator module directly
spec = importlib.util.spec_from_file_location(
    "grade_validator",
    "/home/parrot/code/draft-queen/src/data_pipeline/quality/grade_validator.py"
)
grade_validator_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(grade_validator_module)

GradeValidator = grade_validator_module.GradeValidator
GradeValidationResult = grade_validator_module.GradeValidationResult
GradeOutlierSeverity = grade_validator_module.GradeOutlierSeverity


class TestGradeValidator:
    """Test cases for GradeValidator."""
    
    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        return Mock()
    
    @pytest.fixture
    def validator(self, mock_session):
        """Create validator instance."""
        return GradeValidator(mock_session)
    
    def test_validate_grade_range_pff_valid(self, validator):
        """Test PFF grade within valid range (0-100)."""
        result = validator.validate_grade_range("prospect-1", 85.5, "pff")
        assert result.is_valid
        assert result.grade_value == 85.5
        assert len(result.violations) == 0
    
    def test_validate_grade_range_pff_below_min(self, validator):
        """Test PFF grade below minimum."""
        result = validator.validate_grade_range("prospect-1", -5.0, "pff")
        assert not result.is_valid
        assert any("outside valid range" in v for v in result.violations)
    
    def test_validate_grade_range_pff_above_max(self, validator):
        """Test PFF grade above maximum."""
        result = validator.validate_grade_range("prospect-1", 105.0, "pff")
        assert not result.is_valid
    
    def test_validate_grade_range_nfl_valid(self, validator):
        """Test NFL.com grade within valid range (5.0-10.0)."""
        result = validator.validate_grade_range("prospect-1", 7.5, "nfl")
        assert result.is_valid
    
    def test_validate_grade_range_unknown_source(self, validator):
        """Test unknown grade source."""
        result = validator.validate_grade_range("prospect-1", 80.0, "unknown_source")
        assert not result.is_valid
        assert any("Unknown grade source" in v for v in result.violations)
    
    def test_detect_outliers_zscore_normal(self, validator):
        """Test grade within normal range (not outlier)."""
        position_grades = [80, 82, 84, 86, 88, 90, 92, 85, 87]
        result = validator.detect_outliers_zscore(
            "prospect-1", 85, "QB", "pff", position_grades
        )
        assert result.is_valid
        assert len(result.outliers) == 0
        assert result.severity == GradeOutlierSeverity.NORMAL
    
    def test_detect_outliers_zscore_warning(self, validator):
        """Test grade 2 std devs from mean (warning severity)."""
        # Mean ≈ 85, std dev ≈ 5
        position_grades = [80, 82, 84, 85, 86, 86, 87, 88, 90]
        grade = 70  # Approximately 3 std devs below mean
        result = validator.detect_outliers_zscore(
            "prospect-1", grade, "QB", "pff", position_grades, threshold_std_dev=2.0
        )
        assert len(result.outliers) > 0
        assert "z_score_outlier" in str(result.outliers)
    
    def test_detect_outliers_zscore_critical(self, validator):
        """Test grade 3 std devs from mean (critical severity)."""
        position_grades = [82, 83, 84, 85, 86, 87, 88, 89, 90]
        grade = 60  # Extremely low
        result = validator.detect_outliers_zscore(
            "prospect-1", grade, "QB", "pff", position_grades, threshold_std_dev=2.0
        )
        assert result.severity == GradeOutlierSeverity.CRITICAL
    
    def test_detect_outliers_insufficient_data(self, validator):
        """Test outlier detection with insufficient data."""
        result = validator.detect_outliers_zscore(
            "prospect-1", 85, "QB", "pff", [85], threshold_std_dev=2.0
        )
        assert result.is_valid
        assert len(result.outliers) == 0  # No detection with < 3 grades
    
    def test_detect_grade_change_no_prior(self, validator):
        """Test grade change when no prior grade exists."""
        result = validator.detect_grade_change(
            "prospect-1", 85.0, None, "pff", "QB"
        )
        assert result.is_valid
        assert result.grade_change is None
        assert len(result.outliers) == 0
    
    def test_detect_grade_change_small_change(self, validator):
        """Test small grade change (< threshold)."""
        result = validator.detect_grade_change(
            "prospect-1", 85.0, 84.0, "pff", "QB",
            change_threshold_percentage=20.0
        )
        assert result.is_valid
        assert result.grade_change == 1.0
        assert result.change_percentage == pytest.approx(1.2, abs=0.01)  # 1/84 ≈ 1.2%
        assert len(result.outliers) == 0  # Below 20% threshold
    
    def test_detect_grade_change_large_change_warning(self, validator):
        """Test large grade change (warning severity)."""
        result = validator.detect_grade_change(
            "prospect-1", 65.0, 85.0, "pff", "QB",
            change_threshold_percentage=20.0
        )
        assert len(result.outliers) > 0
        assert result.severity == GradeOutlierSeverity.WARNING
        assert "suspicious_grade_change" in str(result.outliers)
    
    def test_detect_grade_change_extreme_change_critical(self, validator):
        """Test extreme grade change (critical severity)."""
        result = validator.detect_grade_change(
            "prospect-1", 42.5, 85.0, "pff", "QB",
            change_threshold_percentage=20.0
        )
        assert result.severity == GradeOutlierSeverity.CRITICAL  # > 50%
    
    def test_validate_grade_completeness_has_required(self, validator):
        """Test completeness when prospect has required sources."""
        result = validator.validate_grade_completeness(
            "prospect-1", ["pff"], required_sources=["pff"]
        )
        assert result.is_valid
        assert len(result.violations) == 0
    
    def test_validate_grade_completeness_missing_required(self, validator):
        """Test completeness when required source missing."""
        result = validator.validate_grade_completeness(
            "prospect-1", ["espn"], required_sources=["pff", "espn"]
        )
        assert not result.is_valid
        assert any("Missing grades from required sources" in v for v in result.violations)
    
    def test_validate_grade_completeness_no_grades(self, validator):
        """Test completeness when no grades exist."""
        result = validator.validate_grade_completeness(
            "prospect-1", [], required_sources=["pff"]
        )
        assert not result.is_valid
        assert result.severity == GradeOutlierSeverity.CRITICAL
    
    def test_validate_prospect_grades_comprehensive(self, validator):
        """Test comprehensive multi-source validation."""
        grades_dict = {
            "pff": 88,
            "espn": 82,
            "nfl": 8.2,
        }
        position_grades = {
            "pff": [80, 82, 84, 86, 88, 90],
            "espn": [75, 78, 80, 82, 85],
            "nfl": [7.5, 7.8, 8.0, 8.2, 8.5],
        }
        prior_grades = {
            "pff": 86,
            "espn": 80,
        }
        
        result = validator.validate_prospect_grades(
            "prospect-1", "QB", grades_dict, position_grades, prior_grades
        )
        
        assert result.is_valid
        assert result.position == "QB"
        assert validator.stats["total_validated"] == 1
        assert validator.stats["valid"] == 1
    
    def test_validate_prospect_grades_with_violations(self, validator):
        """Test validation with multiple violations."""
        grades_dict = {
            "pff": 105,  # Out of range
        }
        position_grades = {"pff": [85, 86, 87, 88]}
        
        result = validator.validate_prospect_grades(
            "prospect-1", "QB", grades_dict, position_grades
        )
        
        assert not result.is_valid
        assert len(result.violations) > 0
        assert validator.stats["invalid"] == 1
    
    def test_get_stats(self, validator):
        """Test stats tracking."""
        # Run some validations
        validator.validate_grade_range("p1", 85, "pff")
        validator.validate_grade_range("p2", 105, "pff")
        
        stats = validator.get_stats()
        assert "total_validated" in stats
        assert "valid" in stats
        assert "invalid" in stats
        assert "outliers" in stats
    
    def test_outlier_severity_values(self):
        """Test outlier severity enum values."""
        assert GradeOutlierSeverity.NORMAL.value == "normal"
        assert GradeOutlierSeverity.WARNING.value == "warning"
        assert GradeOutlierSeverity.CRITICAL.value == "critical"
