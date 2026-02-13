"""Data quality rules engine with validation and outlier detection.

Implements configurable business logic rules, consistency validation,
and statistical outlier detection (z-score and IQR methods) for prospect data.

Flags rule violations for quarantine workflow while tracking rule changes
and maintaining audit trail.
"""

import logging
import statistics
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Tuple
from datetime import datetime


logger = logging.getLogger(__name__)


class RuleSeverity(Enum):
    """Severity levels for rule violations."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class OutlierMethod(Enum):
    """Methods for outlier detection."""

    Z_SCORE = "z_score"
    IQR = "interquartile_range"
    PERCENTILE = "percentile"


@dataclass
class RuleViolation:
    """Record of a single rule violation."""

    prospect_id: str
    prospect_name: str
    rule_name: str
    rule_category: str
    severity: RuleSeverity
    field_name: str
    field_value: Any
    expected_condition: str
    violation_details: str
    detected_at: datetime = field(default_factory=datetime.utcnow)
    quarantined: bool = False
    review_status: str = "pending"  # pending, approved, rejected, waived
    review_notes: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "prospect_id": self.prospect_id,
            "prospect_name": self.prospect_name,
            "rule_name": self.rule_name,
            "rule_category": self.rule_category,
            "severity": self.severity.value,
            "field_name": self.field_name,
            "field_value": str(self.field_value),
            "expected_condition": self.expected_condition,
            "violation_details": self.violation_details,
            "detected_at": self.detected_at.isoformat(),
            "quarantined": self.quarantined,
            "review_status": self.review_status,
            "review_notes": self.review_notes,
        }


@dataclass
class DataQualityRule:
    """Base data quality rule."""

    rule_id: str
    rule_name: str
    rule_category: str
    severity: RuleSeverity
    description: str
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    modified_at: datetime = field(default_factory=datetime.utcnow)

    def validate(self, prospect: Dict[str, Any]) -> Optional[RuleViolation]:
        """Validate prospect against rule.

        Returns:
            RuleViolation if validation fails, None if passes
        """
        raise NotImplementedError


@dataclass
class BusinessLogicRule(DataQualityRule):
    """Rule enforcing business logic constraints."""

    field_name: str = ""
    operator: str = ""  # "==", "!=", "<", ">", "<=", ">=", "in", "not_in", "contains"
    expected_value: Any = None

    def validate(self, prospect: Dict[str, Any]) -> Optional[RuleViolation]:
        """Validate prospect against business logic rule."""
        if not self.enabled:
            return None

        field_value = prospect.get(self.field_name)
        if field_value is None:
            return None

        violation = self._check_condition(field_value)
        if violation:
            return RuleViolation(
                prospect_id=prospect.get("prospect_id", ""),
                prospect_name=prospect.get("name", "Unknown"),
                rule_name=self.rule_name,
                rule_category=self.rule_category,
                severity=self.severity,
                field_name=self.field_name,
                field_value=field_value,
                expected_condition=f"{self.field_name} {self.operator} {self.expected_value}",
                violation_details=violation,
            )
        return None

    def _check_condition(self, value: Any) -> Optional[str]:
        """Check if value violates condition.

        Returns:
            Description of violation if violated, None if passes
        """
        try:
            if self.operator == "==":
                if value != self.expected_value:
                    return f"Expected {self.expected_value}, got {value}"
            elif self.operator == "!=":
                if value == self.expected_value:
                    return f"Expected not {self.expected_value}"
            elif self.operator == "<":
                if not (value < self.expected_value):
                    return f"Expected < {self.expected_value}, got {value}"
            elif self.operator == ">":
                if not (value > self.expected_value):
                    return f"Expected > {self.expected_value}, got {value}"
            elif self.operator == "<=":
                if not (value <= self.expected_value):
                    return f"Expected <= {self.expected_value}, got {value}"
            elif self.operator == ">=":
                if not (value >= self.expected_value):
                    return f"Expected >= {self.expected_value}, got {value}"
            elif self.operator == "in":
                if value not in self.expected_value:
                    return f"Expected value in {self.expected_value}, got {value}"
            elif self.operator == "not_in":
                if value in self.expected_value:
                    return f"Expected value not in {self.expected_value}"
            elif self.operator == "contains":
                if self.expected_value not in str(value):
                    return f"Expected to contain '{self.expected_value}'"
        except Exception as e:
            logger.error(f"Error checking condition: {e}")
            return f"Error validating: {str(e)}"

        return None


@dataclass
class ConsistencyRule(DataQualityRule):
    """Rule checking consistency between fields."""

    field1: str = ""
    field2: str = ""
    relationship: str = ""  # "equals", "proportional_to", "inverse_proportional"
    tolerance: Optional[float] = None  # For proportional checks

    def validate(self, prospect: Dict[str, Any]) -> Optional[RuleViolation]:
        """Validate consistency between fields."""
        if not self.enabled:
            return None

        value1 = prospect.get(self.field1)
        value2 = prospect.get(self.field2)

        if value1 is None or value2 is None:
            return None

        violation = self._check_consistency(value1, value2)
        if violation:
            return RuleViolation(
                prospect_id=prospect.get("prospect_id", ""),
                prospect_name=prospect.get("name", "Unknown"),
                rule_name=self.rule_name,
                rule_category=self.rule_category,
                severity=self.severity,
                field_name=f"{self.field1}_vs_{self.field2}",
                field_value=f"{self.field1}={value1}, {self.field2}={value2}",
                expected_condition=f"{self.field1} {self.relationship} {self.field2}",
                violation_details=violation,
            )
        return None

    def _check_consistency(self, value1: Any, value2: Any) -> Optional[str]:
        """Check if values are consistent.

        Returns:
            Description of inconsistency if found, None if consistent
        """
        try:
            if self.relationship == "equals":
                if value1 != value2:
                    return f"{self.field1} ({value1}) != {self.field2} ({value2})"
            elif self.relationship == "proportional_to":
                ratio = float(value1) / float(value2) if value2 != 0 else float("inf")
                if self.tolerance and abs(ratio - 1.0) > self.tolerance:
                    return f"Ratio deviation: {ratio:.2f} > tolerance {self.tolerance}"
            elif self.relationship == "inverse_proportional":
                product = float(value1) * float(value2)
                if self.tolerance and abs(product) > self.tolerance:
                    return f"Product {product:.2f} exceeds tolerance"
        except Exception as e:
            return f"Error checking consistency: {str(e)}"

        return None


@dataclass
class OutlierRule(DataQualityRule):
    """Rule detecting statistical outliers in a field."""

    field_name: str = ""
    method: OutlierMethod = OutlierMethod.Z_SCORE
    threshold: float = 3.0  # Z-score or IQR multiplier
    population_field: str = "position"  # Group outliers by field (e.g., position)

    def validate(self, prospect: Dict[str, Any], population_stats: Optional[Dict[str, Any]] = None) -> Optional[
        RuleViolation
    ]:
        """Validate prospect for outliers.

        Args:
            prospect: Prospect record
            population_stats: Pre-calculated population statistics

        Returns:
            RuleViolation if outlier detected, None otherwise
        """
        if not self.enabled or not population_stats:
            return None

        field_value = prospect.get(self.field_name)
        if field_value is None:
            return None

        try:
            field_value = float(field_value)
        except (ValueError, TypeError):
            return None

        population_key = prospect.get(self.population_field, "all")
        pop_stats_by_field = population_stats.get(population_key, {})

        # Get stats for this specific field
        field_stats = pop_stats_by_field.get(self.field_name)
        if not field_stats:
            return None

        is_outlier, details = self._detect_outlier(field_value, field_stats)
        if is_outlier:
            return RuleViolation(
                prospect_id=prospect.get("prospect_id", ""),
                prospect_name=prospect.get("name", "Unknown"),
                rule_name=self.rule_name,
                rule_category=self.rule_category,
                severity=self.severity,
                field_name=self.field_name,
                field_value=field_value,
                expected_condition=f"{self.field_name} within normal range ({self.method.value})",
                violation_details=details,
            )
        return None

    def _detect_outlier(self, value: float, stats: Dict[str, float]) -> Tuple[bool, str]:
        """Detect if value is outlier using configured method.

        Returns:
            (is_outlier, details_string)
        """
        if self.method == OutlierMethod.Z_SCORE:
            mean = stats.get("mean", 0)
            stdev = stats.get("stdev", 0)

            if stdev == 0:
                return False, ""

            z_score = abs((value - mean) / stdev)
            is_outlier = z_score > self.threshold

            return is_outlier, f"Z-score: {z_score:.2f} (threshold: {self.threshold})"

        elif self.method == OutlierMethod.IQR:
            q1 = stats.get("q1")
            q3 = stats.get("q3")

            if q1 is None or q3 is None:
                return False, ""

            iqr = q3 - q1
            lower_bound = q1 - (self.threshold * iqr)
            upper_bound = q3 + (self.threshold * iqr)

            is_outlier = value < lower_bound or value > upper_bound

            return (
                is_outlier,
                f"Value {value} outside bounds [{lower_bound:.2f}, {upper_bound:.2f}]",
            )

        elif self.method == OutlierMethod.PERCENTILE:
            p5 = stats.get("percentile_5")
            p95 = stats.get("percentile_95")

            if p5 is None or p95 is None:
                return False, ""

            is_outlier = value < p5 or value > p95

            return is_outlier, f"Value {value} outside 5-95 percentile range [{p5:.2f}, {p95:.2f}]"

        return False, ""


class DataQualityRulesEngine:
    """Main engine for data quality rule validation and management.

    Manages:
    - Rule definition and versioning
    - Rule validation against prospect data
    - Violation tracking and quarantine
    - Statistical outlier detection
    - Audit trail for rule changes
    """

    def __init__(self):
        """Initialize rules engine."""
        self.rules: Dict[str, DataQualityRule] = {}
        self.violations: List[RuleViolation] = []
        self.quarantined_prospects: set = set()
        self.population_stats: Dict[str, Dict[str, float]] = {}

    def register_rule(self, rule: DataQualityRule) -> None:
        """Register a new rule."""
        self.rules[rule.rule_id] = rule
        logger.info(f"Registered rule: {rule.rule_name}")

    def register_rules_batch(self, rules: List[DataQualityRule]) -> None:
        """Register multiple rules at once."""
        for rule in rules:
            self.register_rule(rule)

    def validate_prospect(self, prospect: Dict[str, Any]) -> List[RuleViolation]:
        """Validate prospect against all enabled rules.

        Args:
            prospect: Prospect record

        Returns:
            List of rule violations (empty if no violations)
        """
        violations = []

        for rule in self.rules.values():
            if not rule.enabled:
                continue

            try:
                # Outlier rules need population stats
                if isinstance(rule, OutlierRule):
                    violation = rule.validate(prospect, self.population_stats)
                else:
                    violation = rule.validate(prospect)

                if violation:
                    violations.append(violation)
                    self.violations.append(violation)
            except Exception as e:
                logger.error(f"Error validating rule {rule.rule_name}: {e}")

        return violations

    def validate_dataset(self, prospects: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate entire dataset.

        Args:
            prospects: List of prospect records

        Returns:
            Dictionary with validation summary
        """
        # First pass: calculate population statistics for outlier detection
        self._calculate_population_stats(prospects)

        # Second pass: validate all prospects
        total_violations = 0
        violations_by_severity = {}
        violated_prospects = set()

        for prospect in prospects:
            violations = self.validate_prospect(prospect)
            if violations:
                total_violations += len(violations)
                violated_prospects.add(prospect.get("prospect_id"))

                for violation in violations:
                    severity = violation.severity.value
                    violations_by_severity[severity] = violations_by_severity.get(severity, 0) + 1

                    if violation.severity in [RuleSeverity.ERROR, RuleSeverity.CRITICAL]:
                        violation.quarantined = True
                        self.quarantined_prospects.add(prospect.get("prospect_id"))

        return {
            "total_records": len(prospects),
            "total_violations": total_violations,
            "violated_prospects": len(violated_prospects),
            "quarantined_prospects": len(self.quarantined_prospects),
            "violations_by_severity": violations_by_severity,
        }

    def get_violations_for_prospect(self, prospect_id: str) -> List[RuleViolation]:
        """Get all violations for a prospect."""
        return [v for v in self.violations if v.prospect_id == prospect_id]

    def get_quarantined_prospects(self) -> List[str]:
        """Get list of quarantined prospect IDs."""
        return list(self.quarantined_prospects)

    def is_prospect_quarantined(self, prospect_id: str) -> bool:
        """Check if prospect is quarantined."""
        return prospect_id in self.quarantined_prospects

    def review_violation(
        self,
        violation: RuleViolation,
        status: str,
        notes: str = "",
    ) -> None:
        """Update violation review status.

        Args:
            violation: Violation to review
            status: "approved", "rejected", or "waived"
            notes: Review notes
        """
        if status not in ["approved", "rejected", "waived"]:
            raise ValueError(f"Invalid review status: {status}")

        violation.review_status = status
        violation.review_notes = notes

        # If approved and was quarantined, remove from quarantine
        if status == "approved" and violation.prospect_id in self.quarantined_prospects:
            # Check if all violations for this prospect are approved
            all_violations = self.get_violations_for_prospect(violation.prospect_id)
            if all(v.review_status == "approved" for v in all_violations):
                self.quarantined_prospects.discard(violation.prospect_id)

        logger.info(f"Reviewed violation: {violation.rule_name} -> {status}")

    def get_violations_summary(self) -> Dict[str, Any]:
        """Get summary of all violations."""
        total_violations = len(self.violations)

        by_severity = {}
        for severity in RuleSeverity:
            count = sum(1 for v in self.violations if v.severity == severity)
            by_severity[severity.value] = count

        by_rule = {}
        for violation in self.violations:
            by_rule[violation.rule_name] = by_rule.get(violation.rule_name, 0) + 1

        by_review_status = {}
        for violation in self.violations:
            status = violation.review_status
            by_review_status[status] = by_review_status.get(status, 0) + 1

        return {
            "total_violations": total_violations,
            "by_severity": by_severity,
            "by_rule": by_rule,
            "by_review_status": by_review_status,
            "quarantined_prospects": len(self.quarantined_prospects),
        }

    def disable_rule(self, rule_id: str) -> bool:
        """Disable a rule."""
        if rule_id not in self.rules:
            return False

        self.rules[rule_id].enabled = False
        self.rules[rule_id].modified_at = datetime.utcnow()
        logger.info(f"Disabled rule: {rule_id}")
        return True

    def enable_rule(self, rule_id: str) -> bool:
        """Enable a rule."""
        if rule_id not in self.rules:
            return False

        self.rules[rule_id].enabled = True
        self.rules[rule_id].modified_at = datetime.utcnow()
        logger.info(f"Enabled rule: {rule_id}")
        return True

    # Private methods

    def _calculate_population_stats(self, prospects: List[Dict[str, Any]]) -> None:
        """Calculate population statistics for outlier detection."""
        self.population_stats = {}

        # Group prospects by population field (e.g., position)
        populations = {}
        for prospect in prospects:
            position = prospect.get("position", "all")
            if position not in populations:
                populations[position] = []

            # Collect all numeric fields for stats calculation
            populations[position].append(prospect)

        # Calculate stats for each position
        for position, position_prospects in populations.items():
            stats = {}

            # Find all numeric fields
            numeric_fields = set()
            for prospect in position_prospects:
                for key, value in prospect.items():
                    try:
                        float(value)
                        numeric_fields.add(key)
                    except (ValueError, TypeError):
                        pass

            # Calculate stats for each numeric field
            for field in numeric_fields:
                values = []
                for prospect in position_prospects:
                    try:
                        val = float(prospect.get(field))
                        values.append(val)
                    except (ValueError, TypeError):
                        pass

                if len(values) >= 2:
                    stats[field] = {
                        "mean": statistics.mean(values),
                        "stdev": statistics.stdev(values) if len(values) > 1 else 0,
                        "q1": self._percentile(values, 25),
                        "q3": self._percentile(values, 75),
                        "percentile_5": self._percentile(values, 5),
                        "percentile_95": self._percentile(values, 95),
                    }

            self.population_stats[position] = stats

    @staticmethod
    def _percentile(values: List[float], percentile: float) -> float:
        """Calculate percentile of values."""
        sorted_vals = sorted(values)
        index = (percentile / 100) * (len(sorted_vals) - 1)
        lower_index = int(index)
        upper_index = min(lower_index + 1, len(sorted_vals) - 1)

        if lower_index == upper_index:
            return sorted_vals[lower_index]

        weight = index - lower_index
        return sorted_vals[lower_index] * (1 - weight) + sorted_vals[upper_index] * weight
