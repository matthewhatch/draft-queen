"""Unit tests for data reconciliation engine."""

import pytest
from datetime import datetime, timedelta

from data_pipeline.reconciliation.reconciliation_engine import (
    ReconciliationEngine,
    ConflictRecord,
    ConflictSeverity,
    DataSource,
    FieldCategory,
    ResolutionStatus,
    ReconciliationResult,
)


class TestReconciliationEngineBasic:
    """Test basic reconciliation engine functionality."""

    def test_engine_initialization(self):
        """Test engine initializes correctly."""
        engine = ReconciliationEngine()
        assert engine is not None
        assert len(engine.conflicts_detected) == 0
        assert len(engine.conflicts_resolved) == 0

    def test_authority_rules_defined(self):
        """Test authority rules are properly configured."""
        engine = ReconciliationEngine()

        # Combine measurements should be authoritative for NFL.com
        assert (
            engine.AUTHORITY_RULES[FieldCategory.COMBINE_MEASUREMENTS] == DataSource.NFL_COM
        )

        # College stats should be authoritative for Yahoo Sports
        assert (
            engine.AUTHORITY_RULES[FieldCategory.COLLEGE_STATS] == DataSource.YAHOO_SPORTS
        )

        # Injury data should be authoritative for ESPN
        assert engine.AUTHORITY_RULES[FieldCategory.INJURY_DATA] == DataSource.ESPN

    def test_conflict_thresholds_defined(self):
        """Test conflict thresholds are configured."""
        engine = ReconciliationEngine()

        # Height tolerance should be 0.5 inches
        assert engine.CONFLICT_THRESHOLDS["height"]["tolerance_inches"] == 0.5

        # Weight tolerance should be 10 lbs
        assert engine.CONFLICT_THRESHOLDS["weight"]["tolerance_lbs"] == 10


class TestConflictDetection:
    """Test conflict detection logic."""

    def test_detect_height_conflict_within_tolerance(self):
        """Test no conflict detected within tolerance."""
        engine = ReconciliationEngine()

        conflict = engine._detect_conflict(
            prospect_id="P001",
            prospect_name="John Doe",
            field_name="height",
            field_category=FieldCategory.COMBINE_MEASUREMENTS,
            source_a=DataSource.NFL_COM,
            value_a=6.0,
            source_b=DataSource.YAHOO_SPORTS,
            value_b=6.01,  # 0.01 feet = 0.12 inches, within tolerance
        )

        assert conflict is None

    def test_detect_height_conflict_beyond_tolerance(self):
        """Test conflict detected beyond tolerance."""
        engine = ReconciliationEngine()

        conflict = engine._detect_conflict(
            prospect_id="P001",
            prospect_name="John Doe",
            field_name="height",
            field_category=FieldCategory.COMBINE_MEASUREMENTS,
            source_a=DataSource.NFL_COM,
            value_a=6.0,
            source_b=DataSource.YAHOO_SPORTS,
            value_b=6.1,  # 0.1 feet = 1.2 inches, beyond 0.5 inch tolerance
        )

        assert conflict is not None
        assert conflict.severity == ConflictSeverity.HIGH
        assert conflict.field_name == "height"

    def test_detect_weight_conflict(self):
        """Test weight conflict detection."""
        engine = ReconciliationEngine()

        conflict = engine._detect_conflict(
            prospect_id="P001",
            prospect_name="John Doe",
            field_name="weight",
            field_category=FieldCategory.COMBINE_MEASUREMENTS,
            source_a=DataSource.NFL_COM,
            value_a=220,
            source_b=DataSource.YAHOO_SPORTS,
            value_b=235,  # 15 lbs difference, beyond 10 lbs tolerance
        )

        assert conflict is not None
        assert conflict.severity == ConflictSeverity.MEDIUM

    def test_identical_values_no_conflict(self):
        """Test identical values produce no conflict."""
        engine = ReconciliationEngine()

        conflict = engine._detect_conflict(
            prospect_id="P001",
            prospect_name="John Doe",
            field_name="height",
            field_category=FieldCategory.COMBINE_MEASUREMENTS,
            source_a=DataSource.NFL_COM,
            value_a=6.0,
            source_b=DataSource.YAHOO_SPORTS,
            value_b=6.0,
        )

        assert conflict is None


class TestReconciliation:
    """Test reconciliation across sources."""

    def test_reconcile_matching_measurements(self):
        """Test reconciliation with matching measurements."""
        engine = ReconciliationEngine()

        nfl_data = {
            "height": 6.2,
            "weight": 220,
            "name": "Patrick Mahomes",
            "position": "QB",
            "college": "Texas Tech",
        }

        yahoo_data = {
            "height": 6.2,
            "weight": 220,
            "name": "Patrick Mahomes",
            "position": "QB",
            "college": "Texas Tech",
        }

        result = engine.reconcile_measurements(
            prospect_id="P001",
            prospect_name="Patrick Mahomes",
            nfl_data=nfl_data,
            yahoo_data=yahoo_data,
        )

        assert len(result.conflicts) == 0
        assert result.all_conflicts_resolved()
        assert "No conflicts detected" in result.recommendation

    def test_reconcile_conflicting_height(self):
        """Test reconciliation with conflicting height."""
        engine = ReconciliationEngine()

        nfl_data = {
            "height": 6.2,
            "weight": 220,
            "name": "Patrick Mahomes",
            "position": "QB",
            "college": "Texas Tech",
        }

        yahoo_data = {
            "height": 6.0,  # Conflict: 0.2 feet beyond tolerance
            "weight": 220,
            "name": "Patrick Mahomes",
            "position": "QB",
            "college": "Texas Tech",
        }

        result = engine.reconcile_measurements(
            prospect_id="P001",
            prospect_name="Patrick Mahomes",
            nfl_data=nfl_data,
            yahoo_data=yahoo_data,
        )

        assert len(result.conflicts) >= 1
        assert any(c.field_name == "height" for c in result.conflicts)

        # Should resolve to NFL.com (authoritative for measurements)
        height_record = [c for c in result.conflicts if c.field_name == "height"][0]
        assert height_record.resolution_status == ResolutionStatus.RESOLVED_AUTOMATIC
        assert height_record.resolution_source == DataSource.NFL_COM

    def test_reconcile_conflicting_position(self):
        """Test reconciliation with conflicting position (critical)."""
        engine = ReconciliationEngine()

        nfl_data = {
            "height": 6.2,
            "weight": 220,
            "name": "Patrick Mahomes",
            "position": "QB",
            "college": "Texas Tech",
        }

        yahoo_data = {
            "height": 6.2,
            "weight": 220,
            "name": "Patrick Mahomes",
            "position": "WR",  # Critical conflict
            "college": "Texas Tech",
        }

        result = engine.reconcile_measurements(
            prospect_id="P001",
            prospect_name="Patrick Mahomes",
            nfl_data=nfl_data,
            yahoo_data=yahoo_data,
        )

        # Should have position conflict marked critical
        position_conflicts = [c for c in result.conflicts if c.field_name == "position"]
        assert len(position_conflicts) > 0
        assert position_conflicts[0].severity == ConflictSeverity.CRITICAL

    def test_reconcile_name_with_suffix(self):
        """Test reconciliation handles name suffixes (Jr, Sr, etc)."""
        engine = ReconciliationEngine()

        nfl_data = {
            "height": 6.2,
            "weight": 220,
            "name": "Patrick Mahomes II",
            "position": "QB",
            "college": "Texas Tech",
        }

        yahoo_data = {
            "height": 6.2,
            "weight": 220,
            "name": "Patrick Mahomes",
            "position": "QB",
            "college": "Texas Tech",
        }

        result = engine.reconcile_measurements(
            prospect_id="P001",
            prospect_name="Patrick Mahomes",
            nfl_data=nfl_data,
            yahoo_data=yahoo_data,
        )

        # Name suffix difference should be ignored or flagged as low severity
        name_conflicts = [c for c in result.conflicts if c.field_name == "name"]
        assert all(c.severity in [ConflictSeverity.LOW, ConflictSeverity.MEDIUM] for c in name_conflicts)


class TestAuthorityRules:
    """Test authority rule application."""

    def test_authority_rule_measurement(self):
        """Test NFL.com is authoritative for measurements."""
        engine = ReconciliationEngine()

        # Create conflicting heights
        nfl_data = {"height": 6.2, "weight": 220}
        yahoo_data = {"height": 6.0, "weight": 225}

        result = engine.reconcile_measurements(
            prospect_id="P001",
            prospect_name="Test Player",
            nfl_data=nfl_data,
            yahoo_data=yahoo_data,
        )

        # All conflicts should resolve to NFL.com
        height_conflicts = [c for c in result.conflicts if c.field_name == "height"]
        for conflict in height_conflicts:
            assert conflict.resolution_source == DataSource.NFL_COM
            assert conflict.resolution_status == ResolutionStatus.RESOLVED_AUTOMATIC

    def test_resolved_values_mapping(self):
        """Test resolved values are correctly mapped."""
        engine = ReconciliationEngine()

        nfl_data = {"height": 6.2, "weight": 220}
        yahoo_data = {"height": 6.0, "weight": 225}

        result = engine.reconcile_measurements(
            prospect_id="P001",
            prospect_name="Test Player",
            nfl_data=nfl_data,
            yahoo_data=yahoo_data,
        )

        # Check resolved values
        if "height" in result.resolved_values:
            resolved_height, resolved_source = result.resolved_values["height"]
            assert resolved_source == DataSource.NFL_COM
            assert resolved_height == 6.2


class TestConflictRecord:
    """Test conflict record operations."""

    def test_conflict_record_creation(self):
        """Test creating conflict record."""
        conflict = ConflictRecord(
            prospect_id="P001",
            prospect_name="Test Player",
            field_name="height",
            field_category=FieldCategory.COMBINE_MEASUREMENTS,
            source_a=DataSource.NFL_COM,
            value_a=6.2,
            source_b=DataSource.YAHOO_SPORTS,
            value_b=6.0,
            severity=ConflictSeverity.HIGH,
        )

        assert conflict.prospect_id == "P001"
        assert conflict.field_name == "height"
        assert conflict.severity == ConflictSeverity.HIGH
        assert conflict.resolution_status == ResolutionStatus.DETECTED

    def test_conflict_record_to_dict(self):
        """Test converting conflict record to dictionary."""
        conflict = ConflictRecord(
            prospect_id="P001",
            prospect_name="Test Player",
            field_name="height",
            field_category=FieldCategory.COMBINE_MEASUREMENTS,
            source_a=DataSource.NFL_COM,
            value_a=6.2,
            source_b=DataSource.YAHOO_SPORTS,
            value_b=6.0,
            severity=ConflictSeverity.HIGH,
        )

        conflict_dict = conflict.as_dict()

        assert conflict_dict["prospect_id"] == "P001"
        assert conflict_dict["field_name"] == "height"
        assert conflict_dict["severity"] == "high"
        assert "detected_at" in conflict_dict


class TestReconciliationResult:
    """Test reconciliation result operations."""

    def test_result_creation(self):
        """Test creating reconciliation result."""
        result = ReconciliationResult(
            prospect_id="P001",
            prospect_name="Test Player",
        )

        assert result.prospect_id == "P001"
        assert len(result.conflicts) == 0
        assert result.all_conflicts_resolved()

    def test_critical_conflicts_filtering(self):
        """Test filtering critical conflicts."""
        result = ReconciliationResult(
            prospect_id="P001",
            prospect_name="Test Player",
        )

        # Add conflicts of different severities
        result.conflicts.append(
            ConflictRecord(
                prospect_id="P001",
                prospect_name="Test Player",
                field_name="height",
                field_category=FieldCategory.COMBINE_MEASUREMENTS,
                source_a=DataSource.NFL_COM,
                value_a=6.2,
                source_b=DataSource.YAHOO_SPORTS,
                value_b=6.0,
                severity=ConflictSeverity.CRITICAL,
            )
        )

        result.conflicts.append(
            ConflictRecord(
                prospect_id="P001",
                prospect_name="Test Player",
                field_name="weight",
                field_category=FieldCategory.COMBINE_MEASUREMENTS,
                source_a=DataSource.NFL_COM,
                value_a=220,
                source_b=DataSource.YAHOO_SPORTS,
                value_b=225,
                severity=ConflictSeverity.MEDIUM,
            )
        )

        critical = result.critical_conflicts()
        assert len(critical) == 1
        assert critical[0].field_name == "height"

    def test_unresolved_conflicts_tracking(self):
        """Test tracking of unresolved conflicts."""
        result = ReconciliationResult(
            prospect_id="P001",
            prospect_name="Test Player",
        )

        conflict = ConflictRecord(
            prospect_id="P001",
            prospect_name="Test Player",
            field_name="height",
            field_category=FieldCategory.COMBINE_MEASUREMENTS,
            source_a=DataSource.NFL_COM,
            value_a=6.2,
            source_b=DataSource.YAHOO_SPORTS,
            value_b=6.0,
            severity=ConflictSeverity.HIGH,
        )

        result.conflicts.append(conflict)
        assert not result.all_conflicts_resolved()

        # Resolve the conflict
        conflict.resolution_status = ResolutionStatus.RESOLVED_AUTOMATIC
        assert result.all_conflicts_resolved()


class TestConflictSummary:
    """Test conflict summary generation."""

    def test_conflict_summary_empty(self):
        """Test summary with no conflicts."""
        engine = ReconciliationEngine()
        summary = engine.get_conflict_summary()

        assert summary["total_conflicts_detected"] == 0
        assert summary["total_conflicts_resolved"] == 0
        assert summary["unresolved_conflicts"] == 0

    def test_conflict_summary_populated(self):
        """Test summary with tracked conflicts."""
        engine = ReconciliationEngine()

        # Add test conflicts
        nfl_data = {"height": 6.2, "weight": 220}
        yahoo_data = {"height": 6.0, "weight": 225}

        result = engine.reconcile_measurements(
            prospect_id="P001",
            prospect_name="Test Player",
            nfl_data=nfl_data,
            yahoo_data=yahoo_data,
        )

        summary = engine.get_conflict_summary()

        assert summary["total_conflicts_detected"] > 0
        assert summary["unresolved_conflicts"] >= 0


class TestManualOverride:
    """Test manual conflict override functionality."""

    def test_manual_override_conflict(self):
        """Test manually overriding conflict resolution."""
        engine = ReconciliationEngine()

        conflict = ConflictRecord(
            prospect_id="P001",
            prospect_name="Test Player",
            field_name="height",
            field_category=FieldCategory.COMBINE_MEASUREMENTS,
            source_a=DataSource.NFL_COM,
            value_a=6.2,
            source_b=DataSource.YAHOO_SPORTS,
            value_b=6.0,
            severity=ConflictSeverity.HIGH,
        )

        # Override to use Yahoo Sports value
        engine.override_conflict(
            conflict,
            DataSource.YAHOO_SPORTS,
            notes="Yahoo data was more recent",
        )

        assert conflict.resolution_status == ResolutionStatus.RESOLVED_MANUAL
        assert conflict.resolution_source == DataSource.YAHOO_SPORTS
        assert "more recent" in conflict.resolution_notes


class TestCollegeStatsValidation:
    """Test college statistics validation."""

    def test_realistic_college_stats_pass(self):
        """Test realistic college stats pass validation."""
        engine = ReconciliationEngine()

        yahoo_data = {
            "rushing_yards": 1500,
            "rushing_touchdowns": 15,  # 1 TD per 100 yards - realistic
            "passing_yards": 3000,
            "passing_touchdowns": 25,  # 1 TD per 120 yards - realistic
        }

        result = engine.reconcile_measurements(
            prospect_id="P001",
            prospect_name="Test Player",
            yahoo_data=yahoo_data,
        )

        # Should have no stat ratio conflicts
        stat_conflicts = [c for c in result.conflicts if "ratio" in c.field_name]
        assert len(stat_conflicts) == 0

    def test_unrealistic_college_stats_detected(self):
        """Test unrealistic college stats are flagged."""
        engine = ReconciliationEngine()

        yahoo_data = {
            "rushing_yards": 1500,
            "rushing_touchdowns": 50,  # Way too many TDs for yards
        }

        result = engine.reconcile_measurements(
            prospect_id="P001",
            prospect_name="Test Player",
            yahoo_data=yahoo_data,
        )

        # Should have stat ratio conflict
        stat_conflicts = [c for c in result.conflicts if "ratio" in c.field_name]
        assert len(stat_conflicts) > 0


class TestInjuryValidation:
    """Test injury data validation."""

    def test_injury_with_past_return_date(self):
        """Test injury marked Out with past return date is flagged."""
        engine = ReconciliationEngine()

        past_date = datetime.utcnow() - timedelta(days=1)

        espn_data = {
            "severity_label": "Out",
            "return_date": past_date,
        }

        result = engine.reconcile_measurements(
            prospect_id="P001",
            prospect_name="Test Player",
            espn_data=espn_data,
        )

        # Should have injury status conflict
        injury_conflicts = [c for c in result.conflicts if c.field_category == FieldCategory.INJURY_DATA]
        assert len(injury_conflicts) > 0
