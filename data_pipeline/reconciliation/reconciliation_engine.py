"""Data reconciliation and conflict resolution engine for multi-source prospect data.

This module implements conflict detection and resolution across multiple data sources
(NFL.com, Yahoo Sports, ESPN). Establishes authority rules for each field type:
- NFL.com: Authoritative for combine measurements (height, weight, athletic tests)
- Yahoo Sports: Authoritative for college statistics
- ESPN: Authoritative for injury data

Detects conflicts, records them in audit trail, and provides resolution mechanisms.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import logging


logger = logging.getLogger(__name__)


class DataSource(Enum):
    """Enumeration of data sources."""

    NFL_COM = "nfl.com"
    YAHOO_SPORTS = "yahoo_sports"
    ESPN = "espn"
    MANUAL_OVERRIDE = "manual_override"


class FieldCategory(Enum):
    """Categories of prospect data fields."""

    COMBINE_MEASUREMENTS = "combine_measurements"  # Height, weight, arm length, hand size
    ATHLETIC_TESTS = "athletic_tests"  # 40 time, bench, vertical, etc.
    COLLEGE_STATS = "college_stats"  # Passing yards, receptions, etc.
    INJURY_DATA = "injury_data"  # Injury type, severity, return date
    DRAFT_INFO = "draft_info"  # Grade, round projection
    PERSONAL_INFO = "personal_info"  # Name, position, college


class ConflictSeverity(Enum):
    """Severity levels for detected conflicts."""

    LOW = "low"  # Minor discrepancies (< 1% difference)
    MEDIUM = "medium"  # Moderate conflicts (1-5% difference or inconsistent data)
    HIGH = "high"  # Major conflicts (> 5% difference or contradictory data)
    CRITICAL = "critical"  # Data integrity issues (missing required fields, impossible values)


class ResolutionStatus(Enum):
    """Status of conflict resolution."""

    DETECTED = "detected"  # Conflict found but not resolved
    RESOLVED_AUTOMATIC = "resolved_automatic"  # Auto-resolved using rules
    RESOLVED_MANUAL = "resolved_manual"  # Manually overridden
    ESCALATED = "escalated"  # Requires human review
    SUPPRESSED = "suppressed"  # Acknowledged but left as-is


@dataclass
class ConflictRecord:
    """Record of detected data conflict."""

    prospect_id: str
    prospect_name: str
    field_name: str
    field_category: FieldCategory
    source_a: DataSource
    value_a: Any
    source_b: DataSource
    value_b: Any
    severity: ConflictSeverity
    difference_pct: Optional[float] = None  # Percentage difference for numeric values
    detected_at: datetime = field(default_factory=datetime.utcnow)
    resolution_status: ResolutionStatus = ResolutionStatus.DETECTED
    resolution_source: Optional[DataSource] = None
    resolution_notes: Optional[str] = None
    resolved_at: Optional[datetime] = None

    def as_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "prospect_id": self.prospect_id,
            "prospect_name": self.prospect_name,
            "field_name": self.field_name,
            "field_category": self.field_category.value,
            "source_a": self.source_a.value,
            "value_a": str(self.value_a),
            "source_b": self.source_b.value,
            "value_b": str(self.value_b),
            "severity": self.severity.value,
            "difference_pct": self.difference_pct,
            "detected_at": self.detected_at.isoformat(),
            "resolution_status": self.resolution_status.value,
            "resolution_source": self.resolution_source.value if self.resolution_source else None,
            "resolution_notes": self.resolution_notes,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }


@dataclass
class ReconciliationResult:
    """Result of reconciliation between two data records."""

    prospect_id: str
    prospect_name: str
    conflicts: List[ConflictRecord] = field(default_factory=list)
    resolved_values: Dict[str, Tuple[Any, DataSource]] = field(default_factory=dict)
    recommendation: str = ""
    requires_human_review: bool = False
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def critical_conflicts(self) -> List[ConflictRecord]:
        """Get only critical severity conflicts."""
        return [c for c in self.conflicts if c.severity == ConflictSeverity.CRITICAL]

    def all_conflicts_resolved(self) -> bool:
        """Check if all conflicts have been resolved."""
        return all(c.resolution_status != ResolutionStatus.DETECTED for c in self.conflicts)


class ReconciliationEngine:
    """Main reconciliation engine for multi-source prospect data.

    Implements conflict detection and resolution using authority rules.
    """

    # Authority rules: which source is authoritative for each field category
    AUTHORITY_RULES = {
        FieldCategory.COMBINE_MEASUREMENTS: DataSource.NFL_COM,
        FieldCategory.ATHLETIC_TESTS: DataSource.NFL_COM,
        FieldCategory.COLLEGE_STATS: DataSource.YAHOO_SPORTS,
        FieldCategory.INJURY_DATA: DataSource.ESPN,
        FieldCategory.DRAFT_INFO: DataSource.NFL_COM,
        FieldCategory.PERSONAL_INFO: DataSource.NFL_COM,
    }

    # Conflict thresholds for automatic detection
    CONFLICT_THRESHOLDS = {
        "height": {"tolerance_inches": 0.5, "severity": ConflictSeverity.HIGH},
        "weight": {"tolerance_lbs": 10, "severity": ConflictSeverity.MEDIUM},
        "forty_time": {"tolerance_seconds": 0.1, "severity": ConflictSeverity.MEDIUM},
        "bench_press_reps": {"tolerance_reps": 5, "severity": ConflictSeverity.LOW},
        "vertical_jump": {"tolerance_inches": 2.0, "severity": ConflictSeverity.LOW},
        "broad_jump": {"tolerance_inches": 6.0, "severity": ConflictSeverity.LOW},
        "three_cone": {"tolerance_seconds": 0.1, "severity": ConflictSeverity.MEDIUM},
        "shuttle": {"tolerance_seconds": 0.1, "severity": ConflictSeverity.MEDIUM},
    }

    def __init__(self):
        """Initialize reconciliation engine."""
        self.conflicts_detected: List[ConflictRecord] = []
        self.conflicts_resolved: List[ConflictRecord] = []

    def reconcile_measurements(
        self,
        prospect_id: str,
        prospect_name: str,
        nfl_data: Optional[Dict[str, Any]] = None,
        yahoo_data: Optional[Dict[str, Any]] = None,
        espn_data: Optional[Dict[str, Any]] = None,
    ) -> ReconciliationResult:
        """Reconcile prospect data across sources.

        Args:
            prospect_id: Unique prospect identifier
            prospect_name: Prospect name for reference
            nfl_data: Data from NFL.com source
            yahoo_data: Data from Yahoo Sports source
            espn_data: Data from ESPN source

        Returns:
            ReconciliationResult with conflicts and resolutions
        """
        result = ReconciliationResult(prospect_id=prospect_id, prospect_name=prospect_name)

        # Combine measurements (NFL.com vs Yahoo)
        if nfl_data and yahoo_data:
            self._reconcile_combine_measurements(
                prospect_id, prospect_name, nfl_data, yahoo_data, result
            )

        # Personal info (NFL.com vs Yahoo)
        if nfl_data and yahoo_data:
            self._reconcile_personal_info(
                prospect_id, prospect_name, nfl_data, yahoo_data, result
            )

        # College stats (Yahoo vs NFL.com cross-check)
        if yahoo_data:
            self._validate_college_stats(prospect_id, prospect_name, yahoo_data, result)

        # Injury data (ESPN cross-check)
        if espn_data:
            self._validate_injury_data(prospect_id, prospect_name, espn_data, result)

        # Apply authority rules to resolve conflicts
        self._apply_authority_rules(result)

        # Generate recommendations
        self._generate_recommendations(result)

        # Track in history
        self.conflicts_detected.extend(result.conflicts)

        logger.info(
            f"Reconciled {prospect_name} ({prospect_id}): "
            f"{len(result.conflicts)} conflicts, "
            f"{len(result.resolved_values)} resolved values"
        )

        return result

    def _reconcile_combine_measurements(
        self,
        prospect_id: str,
        prospect_name: str,
        nfl_data: Dict[str, Any],
        yahoo_data: Dict[str, Any],
        result: ReconciliationResult,
    ) -> None:
        """Reconcile combine measurements between NFL.com and Yahoo."""
        measurements = ["height", "weight", "arm_length", "hand_size"]

        for measurement in measurements:
            nfl_value = nfl_data.get(measurement)
            yahoo_value = yahoo_data.get(measurement)

            if nfl_value is None or yahoo_value is None:
                continue

            conflict = self._detect_conflict(
                prospect_id,
                prospect_name,
                measurement,
                FieldCategory.COMBINE_MEASUREMENTS,
                DataSource.NFL_COM,
                nfl_value,
                DataSource.YAHOO_SPORTS,
                yahoo_value,
            )

            if conflict:
                result.conflicts.append(conflict)

    def _reconcile_personal_info(
        self,
        prospect_id: str,
        prospect_name: str,
        nfl_data: Dict[str, Any],
        yahoo_data: Dict[str, Any],
        result: ReconciliationResult,
    ) -> None:
        """Reconcile personal info between NFL.com and Yahoo."""
        info_fields = ["name", "position", "college"]

        for field in info_fields:
            nfl_value = nfl_data.get(field)
            yahoo_value = yahoo_data.get(field)

            if not nfl_value or not yahoo_value:
                continue

            # Normalize strings for comparison
            nfl_normalized = str(nfl_value).strip().upper()
            yahoo_normalized = str(yahoo_value).strip().upper()

            if nfl_normalized != yahoo_normalized:
                # Name mismatches might be acceptable (Jr., Sr., etc.)
                if field == "name":
                    # Skip exact match but flag for review
                    if not self._are_names_similar(nfl_value, yahoo_value):
                        conflict = ConflictRecord(
                            prospect_id=prospect_id,
                            prospect_name=prospect_name,
                            field_name=field,
                            field_category=FieldCategory.PERSONAL_INFO,
                            source_a=DataSource.NFL_COM,
                            value_a=nfl_value,
                            source_b=DataSource.YAHOO_SPORTS,
                            value_b=yahoo_value,
                            severity=ConflictSeverity.MEDIUM,
                            difference_pct=None,
                        )
                        result.conflicts.append(conflict)
                else:
                    # Position or college mismatch is critical
                    conflict = ConflictRecord(
                        prospect_id=prospect_id,
                        prospect_name=prospect_name,
                        field_name=field,
                        field_category=FieldCategory.PERSONAL_INFO,
                        source_a=DataSource.NFL_COM,
                        value_a=nfl_value,
                        source_b=DataSource.YAHOO_SPORTS,
                        value_b=yahoo_value,
                        severity=ConflictSeverity.CRITICAL,
                    )
                    result.conflicts.append(conflict)

    def _validate_college_stats(
        self,
        prospect_id: str,
        prospect_name: str,
        yahoo_data: Dict[str, Any],
        result: ReconciliationResult,
    ) -> None:
        """Validate college stats for logical consistency."""
        stats_checks = [
            ("rushing_yards", "rushing_touchdowns", 50),  # TDs per 50 rushing yards
            ("passing_yards", "passing_touchdowns", 50),  # TDs per 50 passing yards
            ("receiving_yards", "receptions", 20),  # Yards per reception
        ]

        for total_field, td_field, threshold in stats_checks:
            total_value = yahoo_data.get(total_field)
            td_value = yahoo_data.get(td_field)

            if not total_value or not td_value or total_value == 0:
                continue

            ratio = total_value / threshold
            if td_value > ratio:
                # Unrealistic TD ratio
                conflict = ConflictRecord(
                    prospect_id=prospect_id,
                    prospect_name=prospect_name,
                    field_name=f"{td_field}_vs_{total_field}_ratio",
                    field_category=FieldCategory.COLLEGE_STATS,
                    source_a=DataSource.YAHOO_SPORTS,
                    value_a=f"{total_field}={total_value}",
                    source_b=DataSource.YAHOO_SPORTS,
                    value_b=f"{td_field}={td_value}",
                    severity=ConflictSeverity.LOW,
                )
                result.conflicts.append(conflict)

    def _validate_injury_data(
        self,
        prospect_id: str,
        prospect_name: str,
        espn_data: Dict[str, Any],
        result: ReconciliationResult,
    ) -> None:
        """Validate injury data for consistency."""
        # Check if resolved injury has return date in future
        status = espn_data.get("severity_label")
        return_date = espn_data.get("return_date")

        if status == "Out" and return_date and return_date < datetime.utcnow():
            # Injury marked as Out but return date is past
            conflict = ConflictRecord(
                prospect_id=prospect_id,
                prospect_name=prospect_name,
                field_name="injury_status_vs_return_date",
                field_category=FieldCategory.INJURY_DATA,
                source_a=DataSource.ESPN,
                value_a="status=Out",
                source_b=DataSource.ESPN,
                value_b=f"return_date={return_date}",
                severity=ConflictSeverity.MEDIUM,
            )
            result.conflicts.append(conflict)

    def _detect_conflict(
        self,
        prospect_id: str,
        prospect_name: str,
        field_name: str,
        field_category: FieldCategory,
        source_a: DataSource,
        value_a: Any,
        source_b: DataSource,
        value_b: Any,
    ) -> Optional[ConflictRecord]:
        """Detect if two values conflict based on thresholds.

        Returns:
            ConflictRecord if conflict detected, None otherwise
        """
        if value_a == value_b:
            return None

        # Get threshold for this field
        threshold_config = self.CONFLICT_THRESHOLDS.get(field_name)
        if not threshold_config:
            # No specific threshold, mark any difference as medium conflict
            return ConflictRecord(
                prospect_id=prospect_id,
                prospect_name=prospect_name,
                field_name=field_name,
                field_category=field_category,
                source_a=source_a,
                value_a=value_a,
                source_b=source_b,
                value_b=value_b,
                severity=ConflictSeverity.MEDIUM,
            )

        # Calculate difference for numeric values
        try:
            val_a = float(value_a)
            val_b = float(value_b)
            difference = abs(val_a - val_b)

            # Check against tolerance
            tolerance_key = list(threshold_config.keys())[0]  # e.g., "tolerance_inches"
            tolerance = threshold_config[tolerance_key]
            severity = threshold_config.get("severity", ConflictSeverity.MEDIUM)

            # Special handling for height (convert feet to inches)
            if field_name == "height":
                # Values are in feet, convert difference to inches
                difference_inches = difference * 12
                if difference_inches > tolerance:
                    difference_pct = (difference / ((val_a + val_b) / 2)) * 100
                    return ConflictRecord(
                        prospect_id=prospect_id,
                        prospect_name=prospect_name,
                        field_name=field_name,
                        field_category=field_category,
                        source_a=source_a,
                        value_a=val_a,
                        source_b=source_b,
                        value_b=val_b,
                        severity=severity,
                        difference_pct=difference_pct,
                    )
            elif difference > tolerance:
                difference_pct = (difference / ((val_a + val_b) / 2)) * 100
                return ConflictRecord(
                    prospect_id=prospect_id,
                    prospect_name=prospect_name,
                    field_name=field_name,
                    field_category=field_category,
                    source_a=source_a,
                    value_a=val_a,
                    source_b=source_b,
                    value_b=val_b,
                    severity=severity,
                    difference_pct=difference_pct,
                )
        except (ValueError, TypeError):
            # Non-numeric values
            if value_a != value_b:
                return ConflictRecord(
                    prospect_id=prospect_id,
                    prospect_name=prospect_name,
                    field_name=field_name,
                    field_category=field_category,
                    source_a=source_a,
                    value_a=value_a,
                    source_b=source_b,
                    value_b=value_b,
                    severity=ConflictSeverity.MEDIUM,
                )

        return None

    def _apply_authority_rules(self, result: ReconciliationResult) -> None:
        """Apply authority rules to resolve conflicts."""
        for conflict in result.conflicts:
            # Skip if already manually resolved
            if conflict.resolution_status == ResolutionStatus.RESOLVED_MANUAL:
                continue

            # Get authoritative source for this field category
            authoritative_source = self.AUTHORITY_RULES.get(conflict.field_category)

            if not authoritative_source:
                conflict.resolution_status = ResolutionStatus.ESCALATED
                conflict.resolution_notes = "No authority rule defined for this field category"
                continue

            # Determine which value to use
            if conflict.source_a == authoritative_source:
                resolved_value = conflict.value_a
                resolved_source = conflict.source_a
            elif conflict.source_b == authoritative_source:
                resolved_value = conflict.value_b
                resolved_source = conflict.source_b
            else:
                # Neither source is authoritative (shouldn't happen)
                conflict.resolution_status = ResolutionStatus.ESCALATED
                conflict.resolution_notes = "Neither source is authoritative"
                continue

            # Mark as resolved
            conflict.resolution_status = ResolutionStatus.RESOLVED_AUTOMATIC
            conflict.resolution_source = resolved_source
            conflict.resolved_at = datetime.utcnow()
            conflict.resolution_notes = f"Applied authority rule: {authoritative_source.value} is authoritative for {conflict.field_category.value}"

            # Track resolved value
            result.resolved_values[conflict.field_name] = (resolved_value, resolved_source)

            self.conflicts_resolved.append(conflict)

    def _generate_recommendations(self, result: ReconciliationResult) -> None:
        """Generate recommendation based on conflicts."""
        critical_conflicts = result.critical_conflicts()

        if not result.conflicts:
            result.recommendation = "✅ No conflicts detected. Data is consistent across sources."
            return

        if critical_conflicts:
            result.requires_human_review = True
            result.recommendation = f"⚠️ CRITICAL: {len(critical_conflicts)} critical conflict(s) require manual review."
            return

        escalated = [c for c in result.conflicts if c.resolution_status == ResolutionStatus.ESCALATED]
        if escalated:
            result.requires_human_review = True
            result.recommendation = f"⚠️ {len(escalated)} conflict(s) escalated for human review."
            return

        high_severity = [c for c in result.conflicts if c.severity == ConflictSeverity.HIGH]
        if high_severity:
            result.recommendation = f"⚠️ {len(high_severity)} high-severity conflict(s) automatically resolved using authority rules."
            return

        result.recommendation = f"✓ {len(result.conflicts)} minor conflict(s) automatically resolved."

    @staticmethod
    def _are_names_similar(name1: str, name2: str) -> bool:
        """Check if two names are similar (handles Jr., Sr., etc.)."""
        # Normalize names by removing suffixes
        suffixes = [" jr", " sr", " ii", " iii", " iv"]
        n1 = str(name1).strip().lower()
        n2 = str(name2).strip().lower()

        for suffix in suffixes:
            n1 = n1.replace(suffix, "")
            n2 = n2.replace(suffix, "")

        return n1 == n2

    def override_conflict(
        self,
        conflict: ConflictRecord,
        chosen_source: DataSource,
        notes: str = "",
    ) -> None:
        """Manually override automatic conflict resolution."""
        conflict.resolution_status = ResolutionStatus.RESOLVED_MANUAL
        conflict.resolution_source = chosen_source
        conflict.resolved_at = datetime.utcnow()
        conflict.resolution_notes = notes

        logger.info(f"Manual override: {conflict.prospect_name} {conflict.field_name} -> {chosen_source.value}")

    def get_conflict_summary(self) -> Dict[str, Any]:
        """Get summary statistics of all conflicts."""
        total_conflicts = len(self.conflicts_detected)
        total_resolved = len(self.conflicts_resolved)

        severity_breakdown = {}
        for severity in ConflictSeverity:
            count = sum(1 for c in self.conflicts_detected if c.severity == severity)
            severity_breakdown[severity.value] = count

        status_breakdown = {}
        for status in ResolutionStatus:
            count = sum(1 for c in self.conflicts_detected if c.resolution_status == status)
            status_breakdown[status.value] = count

        return {
            "total_conflicts_detected": total_conflicts,
            "total_conflicts_resolved": total_resolved,
            "unresolved_conflicts": total_conflicts - total_resolved,
            "severity_breakdown": severity_breakdown,
            "status_breakdown": status_breakdown,
            "requires_review": sum(
                1
                for c in self.conflicts_detected
                if c.resolution_status in [ResolutionStatus.DETECTED, ResolutionStatus.ESCALATED]
            ),
        }
