"""Data validation rules for prospect statistics."""

import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ValidationError:
    """Represents a validation error."""

    field: str
    value: any
    rule: str
    message: str
    severity: str  # "error", "warning"


class ProspectStatValidator:
    """Validates prospect statistics against realistic ranges."""

    # Realistic ranges for college football stats
    STAT_RANGES = {
        # Receiving stats
        "receptions": {"min": 0, "max": 200, "unit": "per season"},
        "total_receptions": {"min": 0, "max": 1000, "unit": "career"},
        # Rushing stats
        "rushes": {"min": 0, "max": 400, "unit": "per season"},
        "total_rushes": {"min": 0, "max": 2000, "unit": "career"},
        # Passing stats
        "pass_attempts": {"min": 0, "max": 800, "unit": "per season"},
        "total_pass_attempts": {"min": 0, "max": 4000, "unit": "career"},
        "pass_completions": {"min": 0, "max": 600, "unit": "per season"},
        # Tackle stats
        "tackles": {"min": 0, "max": 200, "unit": "per season"},
        "sacks": {"min": 0, "max": 30, "unit": "per season"},
        # Defensive stats
        "interceptions": {"min": 0, "max": 10, "unit": "per season"},
        "passes_defended": {"min": 0, "max": 30, "unit": "per season"},
        # Kick stats
        "field_goals": {"min": 0, "max": 50, "unit": "per season"},
        "extra_points": {"min": 0, "max": 150, "unit": "per season"},
    }

    # Position-specific expectations
    POSITION_STAT_EXPECTATIONS = {
        "QB": {
            "pass_attempts": {"min": 300},
            "receptions": {"max": 5},  # QBs shouldn't have many receptions
        },
        "RB": {
            "rushes": {"min": 50},
            "receptions": {"min": 10},
        },
        "WR": {
            "receptions": {"min": 30},
            "rushes": {"max": 10},  # WRs rarely rush
        },
        "TE": {
            "receptions": {"min": 20},
            "rushes": {"max": 10},
        },
        "OL": {
            "receptions": {"max": 0},
            "rushes": {"max": 0},
            "pass_attempts": {"max": 0},
        },
        "DL": {
            "receptions": {"max": 0},
            "rushes": {"max": 0},
        },
        "LB": {
            "receptions": {"max": 5},
            "rushes": {"max": 10},
        },
        "DB": {
            "receptions": {"max": 5},
            "rushes": {"max": 5},
        },
    }

    @classmethod
    def validate_stat(
        cls, field: str, value: Optional[int], strict: bool = True
    ) -> Tuple[bool, Optional[ValidationError]]:
        """
        Validate a single statistic.

        Args:
            field: Stat field name
            value: Stat value
            strict: If True, treat warnings as errors

        Returns:
            Tuple of (is_valid, error)
        """
        if value is None:
            return True, None  # None values are acceptable

        if not isinstance(value, (int, float)):
            return (
                False,
                ValidationError(
                    field=field,
                    value=value,
                    rule="type_check",
                    message=f"Expected int/float, got {type(value).__name__}",
                    severity="error",
                ),
            )

        # Check against stat ranges
        if field in cls.STAT_RANGES:
            range_info = cls.STAT_RANGES[field]
            min_val = range_info.get("min")
            max_val = range_info.get("max")
            unit = range_info.get("unit", "")

            if value < min_val:
                return (
                    False,
                    ValidationError(
                        field=field,
                        value=value,
                        rule="min_value",
                        message=f"{field} below minimum {min_val} ({unit})",
                        severity="error",
                    ),
                )

            if value > max_val:
                return (
                    False,
                    ValidationError(
                        field=field,
                        value=value,
                        rule="max_value",
                        message=f"{field} exceeds maximum {max_val} ({unit})",
                        severity="error",
                    ),
                )

        return True, None

    @classmethod
    def validate_prospect(
        cls, prospect: Dict, strict: bool = True
    ) -> Tuple[bool, List[ValidationError]]:
        """
        Validate all stats for a prospect.

        Args:
            prospect: Prospect dictionary with stats
            strict: If True, treat warnings as errors

        Returns:
            Tuple of (is_valid, errors)
        """
        errors = []

        # Validate required fields
        if not prospect.get("name"):
            errors.append(
                ValidationError(
                    field="name",
                    value=None,
                    rule="required",
                    message="Prospect name is required",
                    severity="error",
                )
            )

        # Validate position
        valid_positions = {
            "QB",
            "RB",
            "WR",
            "TE",
            "OT",
            "OG",
            "C",
            "EDGE",
            "DT",
            "LB",
            "CB",
            "S",
            "K",
            "P",
        }
        if prospect.get("position"):
            if prospect["position"].upper() not in valid_positions:
                errors.append(
                    ValidationError(
                        field="position",
                        value=prospect["position"],
                        rule="valid_position",
                        message=f"Invalid position: {prospect['position']}",
                        severity="error",
                    )
                )

        # Validate college stats
        if "college_stats_by_year" in prospect:
            position = prospect.get("position", "").upper()

            for year_idx, year_stat in enumerate(prospect["college_stats_by_year"]):
                for stat_field, stat_value in year_stat.items():
                    if stat_field == "year":
                        continue

                    is_valid, error = cls.validate_stat(stat_field, stat_value, strict)
                    if not is_valid and error:
                        # Enhance error message with year
                        error.message = f"{error.message} in {year_stat.get('year', 'unknown year')}"
                        errors.append(error)

                    # Check position-specific expectations
                    if position in cls.POSITION_STAT_EXPECTATIONS:
                        position_expectations = cls.POSITION_STAT_EXPECTATIONS[position]

                        if stat_field in position_expectations:
                            expectation = position_expectations[stat_field]

                            min_expected = expectation.get("min")
                            if min_expected and stat_value and stat_value < min_expected:
                                errors.append(
                                    ValidationError(
                                        field=stat_field,
                                        value=stat_value,
                                        rule="position_expectation",
                                        message=f"{stat_field}={stat_value} suspiciously low for {position}",
                                        severity="warning",
                                    )
                                )

                            max_expected = expectation.get("max")
                            if max_expected and stat_value and stat_value > max_expected:
                                errors.append(
                                    ValidationError(
                                        field=stat_field,
                                        value=stat_value,
                                        rule="position_expectation",
                                        message=f"{stat_field}={stat_value} suspiciously high for {position}",
                                        severity="warning",
                                    )
                                )

        # Validate production metrics
        if "production_metrics" in prospect:
            metrics = prospect["production_metrics"]
            for metric_field, metric_value in metrics.items():
                is_valid, error = cls.validate_stat(metric_field, metric_value, strict)
                if not is_valid and error:
                    errors.append(error)

        # Validate performance ranking
        if "performance_ranking" in prospect:
            ranking = prospect["performance_ranking"]
            if ranking is not None:
                if not isinstance(ranking, (int, float)):
                    errors.append(
                        ValidationError(
                            field="performance_ranking",
                            value=ranking,
                            rule="type_check",
                            message="Performance ranking must be numeric",
                            severity="error",
                        )
                    )
                elif ranking < 0 or ranking > 10:
                    errors.append(
                        ValidationError(
                            field="performance_ranking",
                            value=ranking,
                            rule="range_check",
                            message="Performance ranking must be 0-10",
                            severity="error",
                        )
                    )

        # Determine if valid based on error severity
        error_count = sum(1 for e in errors if e.severity == "error")
        warning_count = sum(1 for e in errors if e.severity == "warning")

        is_valid = error_count == 0 and (not strict or warning_count == 0)

        if errors:
            logger.warning(
                f"Validation for '{prospect.get('name')}': "
                f"{error_count} errors, {warning_count} warnings"
            )

        return is_valid, errors

    @classmethod
    def get_validation_summary(
        cls, prospects: List[Dict]
    ) -> Tuple[int, int, int, List[Dict]]:
        """
        Get validation summary for multiple prospects.

        Args:
            prospects: List of prospects to validate

        Returns:
            Tuple of (valid_count, total_count, error_count, error_details)
        """
        valid_count = 0
        total_count = len(prospects)
        error_details = []

        for prospect in prospects:
            is_valid, errors = cls.validate_prospect(prospect, strict=False)

            if is_valid:
                valid_count += 1
            else:
                error_details.append(
                    {
                        "prospect": prospect.get("name", "unknown"),
                        "errors": errors,
                    }
                )

        logger.info(
            f"Validation summary: {valid_count}/{total_count} prospects valid "
            f"({len(error_details)} with issues)"
        )

        return valid_count, total_count, len(error_details), error_details
