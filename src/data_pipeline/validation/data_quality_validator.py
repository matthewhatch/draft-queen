"""Data Quality Validation Framework

Post-transformation validation checks to ensure data integrity and quality in canonical tables.

Validation rules:
- prospect_core: no duplicates, required fields, deduplication
- prospect_grades: range 5.0-10.0, source attribution
- prospect_measurements: height/weight range validation, unit validation
- prospect_college_stats: position-specific stat ranges, completeness
- Overall: null value tracking, outlier detection, freshness
"""

from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


@dataclass
class ValidationRule:
    """Single validation rule definition"""
    field_name: str
    field_type: str  # prospect_core, prospect_grades, measurements, college_stats
    rule_type: str  # range, required, enum, unique, not_null
    rule_config: Dict[str, Any]  # min, max, allowed_values, etc
    is_critical: bool = False  # True = block load, False = warning only


@dataclass
class ValidationResult:
    """Result of running a validation check"""
    rule_name: str
    field_name: str
    entity_type: str
    passed: bool
    error_count: int = 0
    warning_count: int = 0
    message: str = ""
    affected_records: List[UUID] = field(default_factory=list)
    
    def is_critical_failure(self) -> bool:
        """Check if this is a critical failure"""
        return not self.passed and self.error_count > 0


@dataclass
class DataQualityReport:
    """Complete data quality report"""
    extraction_id: UUID
    timestamp: datetime
    total_records_evaluated: int
    validation_results: List[ValidationResult]
    quality_metrics: Dict[str, float]  # completeness %, error rate, etc
    overall_status: str  # PASS, PASS_WITH_WARNINGS, FAIL
    
    def get_pass_rate(self) -> float:
        """Calculate overall pass rate"""
        if not self.validation_results:
            return 100.0
        passed = sum(1 for r in self.validation_results if r.passed)
        return (passed / len(self.validation_results)) * 100
    
    def has_critical_failures(self) -> bool:
        """Check if any critical validations failed"""
        return any(r.is_critical_failure() for r in self.validation_results)


class DataQualityValidator:
    """Comprehensive data quality validation framework"""
    
    # Prospect core validation rules
    PROSPECT_CORE_RULES = {
        "no_duplicate_ids": ValidationRule(
            field_name="id",
            field_type="prospect_core",
            rule_type="unique",
            rule_config={},
            is_critical=True,
        ),
        "required_name_or_source_id": ValidationRule(
            field_name="name_first,name_last,pff_id,nfl_combine_id,cfr_player_id",
            field_type="prospect_core",
            rule_type="required",
            rule_config={},
            is_critical=True,
        ),
        "valid_position": ValidationRule(
            field_name="position",
            field_type="prospect_core",
            rule_type="enum",
            rule_config={
                "allowed": ["QB", "RB", "WR", "TE", "OL", "DL", "EDGE", "LB", "DB"]
            },
            is_critical=False,
        ),
    }
    
    # Prospect grades validation rules
    PROSPECT_GRADES_RULES = {
        "grade_range": ValidationRule(
            field_name="grade",
            field_type="prospect_grades",
            rule_type="range",
            rule_config={"min": Decimal("5.0"), "max": Decimal("10.0")},
            is_critical=False,
        ),
        "source_required": ValidationRule(
            field_name="source",
            field_type="prospect_grades",
            rule_type="required",
            rule_config={},
            is_critical=True,
        ),
        "valid_source": ValidationRule(
            field_name="source",
            field_type="prospect_grades",
            rule_type="enum",
            rule_config={"allowed": ["pff", "nfl_combine", "cfr", "yahoo", "espn"]},
            is_critical=False,
        ),
    }
    
    # Prospect measurements validation rules
    PROSPECT_MEASUREMENTS_RULES = {
        "height_range": ValidationRule(
            field_name="height_inches",
            field_type="prospect_measurements",
            rule_type="range",
            rule_config={"min": 60, "max": 80},
            is_critical=False,
        ),
        "weight_range": ValidationRule(
            field_name="weight_lbs",
            field_type="prospect_measurements",
            rule_type="range",
            rule_config={"min": 160, "max": 350},
            is_critical=False,
        ),
        "arm_length_range": ValidationRule(
            field_name="arm_length_inches",
            field_type="prospect_measurements",
            rule_type="range",
            rule_config={"min": 28, "max": 34},
            is_critical=False,
        ),
        "hand_size_range": ValidationRule(
            field_name="hand_size_inches",
            field_type="prospect_measurements",
            rule_type="range",
            rule_config={"min": 7.5, "max": 10.5},
            is_critical=False,
        ),
    }
    
    # Prospect college stats validation rules (position-specific)
    POSITION_STAT_RANGES = {
        "QB": {
            "passing_attempts": (100, 600),
            "passing_yards": (1000, 5000),
            "passing_touchdowns": (5, 60),
            "rushing_yards": (0, 1000),
        },
        "RB": {
            "rushing_attempts": (100, 400),
            "rushing_yards": (500, 2500),
            "receiving_targets": (20, 200),
            "receiving_yards": (100, 2000),
        },
        "WR": {
            "receiving_targets": (50, 200),
            "receiving_receptions": (30, 150),
            "receiving_yards": (200, 2000),
            "rushing_attempts": (0, 50),
        },
        "TE": {
            "receiving_targets": (30, 150),
            "receiving_receptions": (20, 100),
            "receiving_yards": (100, 1500),
        },
        "DL": {
            "tackles": (20, 200),
            "sacks": (0, 30),
            "tackles_for_loss": (3, 50),
        },
        "EDGE": {
            "sacks": (3, 30),
            "tackles": (20, 150),
            "tackles_for_loss": (5, 50),
        },
        "LB": {
            "tackles": (50, 200),
            "sacks": (0, 30),
            "passes_defended": (0, 50),
        },
        "DB": {
            "interceptions": (0, 15),
            "passes_defended": (0, 50),
            "tackles": (20, 150),
        },
    }
    
    def __init__(self, db_session, logger_instance=None):
        """Initialize validator.
        
        Args:
            db_session: Database session for queries
            logger_instance: Optional logger instance
        """
        self.db = db_session
        self.logger = logger_instance or logging.getLogger(self.__class__.__name__)
    
    async def validate_prospect_core(self) -> ValidationResult:
        """Validate prospect_core table integrity.
        
        Returns:
            ValidationResult with core validation status
        """
        from sqlalchemy import text
        
        # Check for duplicates
        result = await self.db.execute(
            text(
                """
                SELECT COUNT(*) as cnt, name_first, name_last, position, college
                FROM prospect_core
                WHERE status = 'active'
                GROUP BY name_first, name_last, position, college
                HAVING COUNT(*) > 1
                """
            )
        )
        duplicates = await result.fetchall()
        
        passed = len(duplicates) == 0
        error_count = len(duplicates)
        
        return ValidationResult(
            rule_name="prospect_core_duplicates",
            field_name="name_first,name_last,position,college",
            entity_type="prospect_core",
            passed=passed,
            error_count=error_count,
            message=f"Found {error_count} duplicate prospect records" if error_count > 0 else "No duplicates found",
        )
    
    async def validate_prospect_grades(self) -> ValidationResult:
        """Validate prospect_grades table values.
        
        Returns:
            ValidationResult with grades validation status
        """
        from sqlalchemy import text
        
        # Check for out-of-range grades
        result = await self.db.execute(
            text(
                """
                SELECT COUNT(*) as cnt
                FROM prospect_grades
                WHERE grade < 5.0 OR grade > 10.0
                """
            )
        )
        row = await result.fetchone()
        out_of_range_count = row[0] if row else 0
        
        passed = out_of_range_count == 0
        
        return ValidationResult(
            rule_name="prospect_grades_range",
            field_name="grade",
            entity_type="prospect_grades",
            passed=passed,
            error_count=out_of_range_count,
            message=f"Found {out_of_range_count} out-of-range grades" if out_of_range_count > 0 else "All grades in valid range 5.0-10.0",
        )
    
    async def validate_prospect_measurements(self) -> ValidationResult:
        """Validate prospect_measurements table values.
        
        Returns:
            ValidationResult with measurements validation status
        """
        from sqlalchemy import text
        
        # Check for out-of-range measurements
        result = await self.db.execute(
            text(
                """
                SELECT COUNT(*) as cnt
                FROM prospect_measurements
                WHERE 
                    (height_inches < 60 OR height_inches > 80)
                    OR (weight_lbs < 160 OR weight_lbs > 350)
                    OR (arm_length_inches < 28 OR arm_length_inches > 34)
                    OR (hand_size_inches < 7.5 OR hand_size_inches > 10.5)
                """
            )
        )
        row = await result.fetchone()
        out_of_range_count = row[0] if row else 0
        
        passed = out_of_range_count == 0
        
        return ValidationResult(
            rule_name="prospect_measurements_range",
            field_name="height_inches,weight_lbs,arm_length_inches,hand_size_inches",
            entity_type="prospect_measurements",
            passed=passed,
            error_count=out_of_range_count,
            message=f"Found {out_of_range_count} out-of-range measurements" if out_of_range_count > 0 else "All measurements in valid ranges",
        )
    
    async def validate_prospect_college_stats(self) -> ValidationResult:
        """Validate prospect_college_stats with position-specific ranges.
        
        Returns:
            ValidationResult with college stats validation status
        """
        from sqlalchemy import text
        
        # Check for invalid stats per position
        total_issues = 0
        
        for position, stat_ranges in self.POSITION_STAT_RANGES.items():
            for stat_name, (min_val, max_val) in stat_ranges.items():
                result = await self.db.execute(
                    text(
                        f"""
                        SELECT COUNT(*) as cnt
                        FROM prospect_college_stats pcs
                        JOIN prospect_core pc ON pcs.prospect_id = pc.id
                        WHERE pc.position = :pos
                        AND pcs.{stat_name} IS NOT NULL
                        AND (pcs.{stat_name} < :min_val OR pcs.{stat_name} > :max_val)
                        """
                    ),
                    {"pos": position, "min_val": min_val, "max_val": max_val},
                )
                row = await result.fetchone()
                if row:
                    total_issues += row[0]
        
        passed = total_issues == 0
        
        return ValidationResult(
            rule_name="prospect_college_stats_range",
            field_name="position-specific stats",
            entity_type="prospect_college_stats",
            passed=passed,
            error_count=total_issues,
            message=f"Found {total_issues} out-of-range college stats" if total_issues > 0 else "All college stats in valid ranges",
        )
    
    async def calculate_completeness(self, entity_type: str) -> float:
        """Calculate data completeness percentage for entity type.
        
        Args:
            entity_type: Type of entity to check
            
        Returns:
            Completeness percentage (0-100)
        """
        from sqlalchemy import text
        
        if entity_type == "prospect_grades":
            result = await self.db.execute(
                text(
                    """
                    SELECT 
                        COUNT(*) as total,
                        COUNT(grade) as grade_count,
                        COUNT(source) as source_count
                    FROM prospect_grades
                    """
                )
            )
            row = await result.fetchone()
            if row[0] == 0:
                return 100.0
            
            # Calculate average completeness across key fields
            completeness = ((row[1] + row[2]) / (row[0] * 2)) * 100
            return min(completeness, 100.0)
        
        elif entity_type == "prospect_measurements":
            result = await self.db.execute(
                text(
                    """
                    SELECT 
                        COUNT(*) as total,
                        COUNT(height_inches) as height_count,
                        COUNT(weight_lbs) as weight_count,
                        COUNT(arm_length_inches) as arm_count
                    FROM prospect_measurements
                    """
                )
            )
            row = await result.fetchone()
            if row[0] == 0:
                return 100.0
            
            completeness = ((row[1] + row[2] + row[3]) / (row[0] * 3)) * 100
            return min(completeness, 100.0)
        
        elif entity_type == "prospect_college_stats":
            result = await self.db.execute(
                text(
                    """
                    SELECT 
                        COUNT(*) as total,
                        COUNT(season) as season_count,
                        COUNT(college) as college_count
                    FROM prospect_college_stats
                    """
                )
            )
            row = await result.fetchone()
            if row[0] == 0:
                return 100.0
            
            completeness = ((row[1] + row[2]) / (row[0] * 2)) * 100
            return min(completeness, 100.0)
        
        else:
            return 100.0
    
    async def calculate_error_rate(self) -> float:
        """Calculate overall data error rate.
        
        Returns:
            Error rate as percentage
        """
        from sqlalchemy import text
        
        result = await self.db.execute(
            text(
                """
                SELECT 
                    COUNT(*) as total_records,
                    (SELECT COUNT(*) FROM prospect_core WHERE status = 'error') +
                    (SELECT COUNT(*) FROM prospect_grades WHERE is_invalid = true) +
                    (SELECT COUNT(*) FROM prospect_measurements WHERE is_invalid = true) +
                    (SELECT COUNT(*) FROM prospect_college_stats WHERE is_invalid = true)
                    as error_records
                FROM (
                    SELECT * FROM prospect_core
                    UNION ALL
                    SELECT * FROM prospect_grades
                    UNION ALL
                    SELECT * FROM prospect_measurements
                    UNION ALL
                    SELECT * FROM prospect_college_stats
                ) all_records
                """
            )
        )
        row = await result.fetchone()
        
        if row[0] == 0:
            return 0.0
        
        error_rate = (row[1] / row[0]) * 100
        return min(error_rate, 100.0)
    
    async def run_all_validations(self, extraction_id: UUID) -> DataQualityReport:
        """Run all validation checks.
        
        Args:
            extraction_id: ETL extraction ID
            
        Returns:
            Complete data quality report
        """
        # Run validation checks
        results = []
        results.append(await self.validate_prospect_core())
        results.append(await self.validate_prospect_grades())
        results.append(await self.validate_prospect_measurements())
        results.append(await self.validate_prospect_college_stats())
        
        # Calculate quality metrics
        completeness_grades = await self.calculate_completeness("prospect_grades")
        completeness_measurements = await self.calculate_completeness("prospect_measurements")
        completeness_stats = await self.calculate_completeness("prospect_college_stats")
        error_rate = await self.calculate_error_rate()
        
        quality_metrics = {
            "completeness_grades": completeness_grades,
            "completeness_measurements": completeness_measurements,
            "completeness_stats": completeness_stats,
            "error_rate": error_rate,
            "pass_rate": (sum(1 for r in results if r.passed) / len(results) * 100) if results else 0.0,
        }
        
        # Determine overall status
        if any(r.is_critical_failure() for r in results):
            overall_status = "FAIL"
        elif any(not r.passed for r in results):
            overall_status = "PASS_WITH_WARNINGS"
        else:
            overall_status = "PASS"
        
        # Count total records (approximate)
        total_records = sum(
            result.error_count for result in results if result.error_count > 0
        )
        
        return DataQualityReport(
            extraction_id=extraction_id,
            timestamp=datetime.utcnow(),
            total_records_evaluated=total_records,
            validation_results=results,
            quality_metrics=quality_metrics,
            overall_status=overall_status,
        )
    
    async def store_quality_report(self, report: DataQualityReport) -> bool:
        """Store quality report to database.
        
        Args:
            report: DataQualityReport to store
            
        Returns:
            True if successful, False otherwise
        """
        from sqlalchemy import text
        import json
        
        try:
            await self.db.execute(
                text(
                    """
                    INSERT INTO quality_metrics 
                    (extraction_id, timestamp, overall_status, 
                     completeness_grades, completeness_measurements, 
                     completeness_stats, error_rate, pass_rate)
                    VALUES (:extraction_id, :timestamp, :overall_status,
                            :completeness_grades, :completeness_measurements,
                            :completeness_stats, :error_rate, :pass_rate)
                    """
                ),
                {
                    "extraction_id": str(report.extraction_id),
                    "timestamp": report.timestamp,
                    "overall_status": report.overall_status,
                    "completeness_grades": report.quality_metrics.get("completeness_grades", 0),
                    "completeness_measurements": report.quality_metrics.get("completeness_measurements", 0),
                    "completeness_stats": report.quality_metrics.get("completeness_stats", 0),
                    "error_rate": report.quality_metrics.get("error_rate", 0),
                    "pass_rate": report.quality_metrics.get("pass_rate", 0),
                },
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to store quality report: {e}")
            return False
