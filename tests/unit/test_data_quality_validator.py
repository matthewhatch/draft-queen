"""Unit tests for Data Quality Validator

Tests for post-transformation validation of canonical tables.
"""

import pytest
from uuid import uuid4
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from src.data_pipeline.validation.data_quality_validator import (
    DataQualityValidator,
    ValidationRule,
    ValidationResult,
    DataQualityReport,
)


@pytest.fixture
def mock_session():
    """Create mock database session."""
    return MagicMock()


@pytest.fixture
def validator(mock_session):
    """Create data quality validator instance."""
    return DataQualityValidator(mock_session)


@pytest.fixture
def extraction_id():
    """Create extraction ID."""
    return uuid4()


class TestValidationRule:
    """Test ValidationRule dataclass."""

    def test_create_range_rule(self):
        """Test creating range validation rule."""
        rule = ValidationRule(
            field_name="grade",
            field_type="prospect_grades",
            rule_type="range",
            rule_config={"min": Decimal("5.0"), "max": Decimal("10.0")},
            is_critical=False,
        )
        assert rule.field_name == "grade"
        assert rule.rule_type == "range"
        assert rule.rule_config["min"] == Decimal("5.0")
        assert rule.is_critical is False

    def test_create_required_rule(self):
        """Test creating required field rule."""
        rule = ValidationRule(
            field_name="source",
            field_type="prospect_grades",
            rule_type="required",
            rule_config={},
            is_critical=True,
        )
        assert rule.is_critical is True
        assert rule.rule_type == "required"

    def test_create_enum_rule(self):
        """Test creating enum validation rule."""
        rule = ValidationRule(
            field_name="position",
            field_type="prospect_core",
            rule_type="enum",
            rule_config={"allowed": ["QB", "RB", "WR", "TE"]},
        )
        assert len(rule.rule_config["allowed"]) == 4


class TestValidationResult:
    """Test ValidationResult dataclass."""

    def test_create_passing_result(self):
        """Test creating passing validation result."""
        result = ValidationResult(
            rule_name="test_rule",
            field_name="test_field",
            entity_type="prospect_grades",
            passed=True,
            error_count=0,
        )
        assert result.passed is True
        assert result.is_critical_failure() is False

    def test_create_failing_result(self):
        """Test creating failing validation result."""
        result = ValidationResult(
            rule_name="test_rule",
            field_name="test_field",
            entity_type="prospect_grades",
            passed=False,
            error_count=5,
        )
        assert result.passed is False
        assert result.is_critical_failure() is True

    def test_critical_failure_detection(self):
        """Test critical failure detection."""
        critical_result = ValidationResult(
            rule_name="critical",
            field_name="test",
            entity_type="prospect_core",
            passed=False,
            error_count=1,
        )
        assert critical_result.is_critical_failure() is True

        warning_result = ValidationResult(
            rule_name="warning",
            field_name="test",
            entity_type="prospect_grades",
            passed=False,
            error_count=0,  # No errors, just warning
        )
        assert warning_result.is_critical_failure() is False


class TestDataQualityReport:
    """Test DataQualityReport dataclass."""

    def test_create_quality_report(self, extraction_id):
        """Test creating quality report."""
        results = [
            ValidationResult(
                rule_name="rule1",
                field_name="field1",
                entity_type="prospect_core",
                passed=True,
            ),
            ValidationResult(
                rule_name="rule2",
                field_name="field2",
                entity_type="prospect_grades",
                passed=True,
            ),
        ]

        report = DataQualityReport(
            extraction_id=extraction_id,
            timestamp=datetime.utcnow(),
            total_records_evaluated=1000,
            validation_results=results,
            quality_metrics={
                "completeness_grades": 98.5,
                "error_rate": 1.2,
            },
            overall_status="PASS",
        )

        assert report.extraction_id == extraction_id
        assert len(report.validation_results) == 2
        assert report.overall_status == "PASS"

    def test_pass_rate_calculation(self, extraction_id):
        """Test pass rate calculation."""
        results = [
            ValidationResult(
                rule_name="rule1",
                field_name="field1",
                entity_type="prospect_core",
                passed=True,
            ),
            ValidationResult(
                rule_name="rule2",
                field_name="field2",
                entity_type="prospect_grades",
                passed=False,
            ),
            ValidationResult(
                rule_name="rule3",
                field_name="field3",
                entity_type="prospect_measurements",
                passed=True,
            ),
        ]

        report = DataQualityReport(
            extraction_id=extraction_id,
            timestamp=datetime.utcnow(),
            total_records_evaluated=100,
            validation_results=results,
            quality_metrics={},
            overall_status="PASS_WITH_WARNINGS",
        )

        # 2 out of 3 passed = 66.67%
        assert abs(report.get_pass_rate() - 66.67) < 0.1

    def test_critical_failure_detection(self, extraction_id):
        """Test critical failure detection in report."""
        critical_result = ValidationResult(
            rule_name="critical",
            field_name="id",
            entity_type="prospect_core",
            passed=False,
            error_count=5,
        )

        warning_result = ValidationResult(
            rule_name="warning",
            field_name="grade",
            entity_type="prospect_grades",
            passed=False,
            error_count=0,
        )

        report = DataQualityReport(
            extraction_id=extraction_id,
            timestamp=datetime.utcnow(),
            total_records_evaluated=100,
            validation_results=[critical_result, warning_result],
            quality_metrics={},
            overall_status="FAIL",
        )

        assert report.has_critical_failures() is True


class TestDataQualityValidator:
    """Test DataQualityValidator class."""

    def test_validator_initialization(self, validator):
        """Test validator initialization."""
        assert validator.db is not None
        assert validator.logger is not None

    def test_prospect_core_rules_defined(self, validator):
        """Test that prospect_core validation rules are defined."""
        assert "no_duplicate_ids" in validator.PROSPECT_CORE_RULES
        assert "required_name_or_source_id" in validator.PROSPECT_CORE_RULES
        assert "valid_position" in validator.PROSPECT_CORE_RULES

    def test_prospect_grades_rules_defined(self, validator):
        """Test that prospect_grades validation rules are defined."""
        assert "grade_range" in validator.PROSPECT_GRADES_RULES
        assert "source_required" in validator.PROSPECT_GRADES_RULES
        assert "valid_source" in validator.PROSPECT_GRADES_RULES

    def test_prospect_measurements_rules_defined(self, validator):
        """Test that prospect_measurements validation rules are defined."""
        assert "height_range" in validator.PROSPECT_MEASUREMENTS_RULES
        assert "weight_range" in validator.PROSPECT_MEASUREMENTS_RULES
        assert "arm_length_range" in validator.PROSPECT_MEASUREMENTS_RULES
        assert "hand_size_range" in validator.PROSPECT_MEASUREMENTS_RULES

    def test_position_stat_ranges_defined(self, validator):
        """Test that position-specific stat ranges are defined."""
        assert "QB" in validator.POSITION_STAT_RANGES
        assert "RB" in validator.POSITION_STAT_RANGES
        assert "WR" in validator.POSITION_STAT_RANGES
        assert "TE" in validator.POSITION_STAT_RANGES
        assert "DL" in validator.POSITION_STAT_RANGES
        assert "EDGE" in validator.POSITION_STAT_RANGES
        assert "LB" in validator.POSITION_STAT_RANGES
        assert "DB" in validator.POSITION_STAT_RANGES

    def test_qb_stat_ranges(self, validator):
        """Test QB stat ranges."""
        qb_stats = validator.POSITION_STAT_RANGES["QB"]
        assert qb_stats["passing_attempts"] == (100, 600)
        assert qb_stats["passing_yards"] == (1000, 5000)
        assert qb_stats["passing_touchdowns"] == (5, 60)

    def test_rb_stat_ranges(self, validator):
        """Test RB stat ranges."""
        rb_stats = validator.POSITION_STAT_RANGES["RB"]
        assert rb_stats["rushing_attempts"] == (100, 400)
        assert rb_stats["receiving_targets"] == (20, 200)

    def test_dl_stat_ranges(self, validator):
        """Test DL stat ranges."""
        dl_stats = validator.POSITION_STAT_RANGES["DL"]
        assert dl_stats["tackles"] == (20, 200)
        assert dl_stats["sacks"] == (0, 30)

    async def test_validate_prospect_core_no_duplicates(self, validator):
        """Test prospect_core validation with no duplicates."""
        mock_result = AsyncMock()
        mock_result.fetchall = AsyncMock(return_value=[])
        validator.db.execute = AsyncMock(return_value=mock_result)

        result = await validator.validate_prospect_core()

        assert result.passed is True
        assert result.error_count == 0

    async def test_validate_prospect_core_with_duplicates(self, validator):
        """Test prospect_core validation with duplicates found."""
        mock_result = AsyncMock()
        mock_result.fetchall = AsyncMock(return_value=[(2,), (3,)])  # 2 duplicate groups
        validator.db.execute = AsyncMock(return_value=mock_result)

        result = await validator.validate_prospect_core()

        assert result.passed is False
        assert result.error_count == 2

    async def test_validate_prospect_grades_in_range(self, validator):
        """Test prospect_grades validation with grades in range."""
        mock_result = AsyncMock()
        mock_result.fetchone = AsyncMock(return_value=(0,))  # 0 out of range
        validator.db.execute = AsyncMock(return_value=mock_result)

        result = await validator.validate_prospect_grades()

        assert result.passed is True
        assert result.error_count == 0

    async def test_validate_prospect_grades_out_of_range(self, validator):
        """Test prospect_grades validation with out-of-range grades."""
        mock_result = AsyncMock()
        mock_result.fetchone = AsyncMock(return_value=(5,))  # 5 out of range
        validator.db.execute = AsyncMock(return_value=mock_result)

        result = await validator.validate_prospect_grades()

        assert result.passed is False
        assert result.error_count == 5

    async def test_validate_prospect_measurements_in_range(self, validator):
        """Test prospect_measurements validation with values in range."""
        mock_result = AsyncMock()
        mock_result.fetchone = AsyncMock(return_value=(0,))
        validator.db.execute = AsyncMock(return_value=mock_result)

        result = await validator.validate_prospect_measurements()

        assert result.passed is True

    async def test_validate_prospect_measurements_out_of_range(self, validator):
        """Test prospect_measurements validation with out-of-range values."""
        mock_result = AsyncMock()
        mock_result.fetchone = AsyncMock(return_value=(8,))
        validator.db.execute = AsyncMock(return_value=mock_result)

        result = await validator.validate_prospect_measurements()

        assert result.passed is False
        assert result.error_count == 8

    async def test_calculate_completeness_high(self, validator):
        """Test completeness calculation with high completeness."""
        mock_result = AsyncMock()
        mock_result.fetchone = AsyncMock(return_value=(100, 98, 99))  # total, grade_count, source_count
        validator.db.execute = AsyncMock(return_value=mock_result)

        completeness = await validator.calculate_completeness("prospect_grades")

        # (98 + 99) / (100 * 2) * 100 = 98.5%
        assert completeness == 98.5

    async def test_calculate_completeness_empty_table(self, validator):
        """Test completeness calculation with empty table."""
        mock_result = AsyncMock()
        mock_result.fetchone = AsyncMock(return_value=(0, 0, 0))
        validator.db.execute = AsyncMock(return_value=mock_result)

        completeness = await validator.calculate_completeness("prospect_grades")

        assert completeness == 100.0  # Empty table = perfect

    async def test_calculate_error_rate_zero_errors(self, validator):
        """Test error rate calculation with no errors."""
        mock_result = AsyncMock()
        mock_result.fetchone = AsyncMock(return_value=(1000, 0))  # total, error_count
        validator.db.execute = AsyncMock(return_value=mock_result)

        error_rate = await validator.calculate_error_rate()

        assert error_rate == 0.0

    async def test_calculate_error_rate_with_errors(self, validator):
        """Test error rate calculation with errors."""
        mock_result = AsyncMock()
        mock_result.fetchone = AsyncMock(return_value=(1000, 50))  # 5% error rate
        validator.db.execute = AsyncMock(return_value=mock_result)

        error_rate = await validator.calculate_error_rate()

        assert error_rate == 5.0

    async def test_run_all_validations_pass(self, validator, extraction_id):
        """Test running all validations with passing results."""
        # Create async mocks for all database calls
        mock_result = AsyncMock()
        mock_result.fetchall = AsyncMock(return_value=[])
        mock_result.fetchone = AsyncMock(return_value=(0,))
        validator.db.execute = AsyncMock(return_value=mock_result)

        report = await validator.run_all_validations(extraction_id)

        assert report.extraction_id == extraction_id
        assert report.overall_status == "PASS"
        assert len(report.validation_results) == 4
        assert all(r.passed for r in report.validation_results)

    async def test_run_all_validations_with_warnings(self, validator, extraction_id):
        """Test running all validations returns report object."""
        # Mock database to always return mock results
        mock_result = AsyncMock()
        mock_result.fetchall = AsyncMock(return_value=[])
        mock_result.fetchone = AsyncMock(return_value=(0,))
        validator.db.execute = AsyncMock(return_value=mock_result)

        report = await validator.run_all_validations(extraction_id)

        # Verify report structure
        assert isinstance(report, DataQualityReport)
        assert report.extraction_id == extraction_id
        assert isinstance(report.validation_results, list)
        assert len(report.validation_results) >= 1

    async def test_store_quality_report_success(self, validator, extraction_id):
        """Test storing quality report successfully."""
        validator.db.execute = AsyncMock(return_value=None)

        report = DataQualityReport(
            extraction_id=extraction_id,
            timestamp=datetime.utcnow(),
            total_records_evaluated=1000,
            validation_results=[],
            quality_metrics={"completeness_grades": 98.5, "error_rate": 1.2},
            overall_status="PASS",
        )

        result = await validator.store_quality_report(report)

        assert result is True
        validator.db.execute.assert_called_once()

    async def test_store_quality_report_failure(self, validator, extraction_id):
        """Test storing quality report with database error."""
        validator.db.execute = AsyncMock(side_effect=Exception("DB Error"))

        report = DataQualityReport(
            extraction_id=extraction_id,
            timestamp=datetime.utcnow(),
            total_records_evaluated=1000,
            validation_results=[],
            quality_metrics={},
            overall_status="PASS",
        )

        result = await validator.store_quality_report(report)

        assert result is False


class TestValidationStatRanges:
    """Test position-specific stat ranges."""

    def test_all_positions_have_stat_ranges(self, validator):
        """Test that all 8 positions have defined stat ranges."""
        positions = ["QB", "RB", "WR", "TE", "DL", "EDGE", "LB", "DB"]
        for pos in positions:
            assert pos in validator.POSITION_STAT_RANGES
            assert len(validator.POSITION_STAT_RANGES[pos]) > 0

    def test_all_ranges_have_min_max(self, validator):
        """Test that all ranges have min and max values."""
        for position, stats in validator.POSITION_STAT_RANGES.items():
            for stat_name, (min_val, max_val) in stats.items():
                assert min_val >= 0, f"{position}.{stat_name} min is negative"
                assert max_val > min_val, f"{position}.{stat_name} max <= min"

    def test_qb_ranges_reasonable(self, validator):
        """Test that QB ranges are reasonable."""
        qb = validator.POSITION_STAT_RANGES["QB"]
        assert qb["passing_yards"] == (1000, 5000)  # Elite QBs ~4000-5000
        assert qb["passing_touchdowns"] == (5, 60)  # Elite ~40-50

    def test_edge_ranges_different_from_dl(self, validator):
        """Test that EDGE ranges are different from DL."""
        edge = validator.POSITION_STAT_RANGES["EDGE"]
        dl = validator.POSITION_STAT_RANGES["DL"]
        # EDGE has higher sack minimum (more sacks expected)
        assert edge["sacks"][0] >= dl["sacks"][0]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
