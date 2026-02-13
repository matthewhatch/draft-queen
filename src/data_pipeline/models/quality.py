"""Quality tracking ORM models.

Database models for quality rules, alerts, grade history tracking,
and quality metrics aggregation.

US-044: Enhanced Data Quality for Multi-Source Grades
"""

from datetime import datetime
from typing import Optional, List
from uuid import uuid4
from sqlalchemy import (
    Column, String, Float, Integer, Boolean, DateTime,
    ForeignKey, UniqueConstraint, Index, Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from enum import Enum

from src.backend.database.models import Base


class AlertType(Enum):
    """Type of quality alert."""
    OUTLIER = "outlier"
    GRADE_CHANGE = "grade_change"
    COMPLETENESS = "completeness"
    RANGE_VIOLATION = "range_violation"
    MANUAL_FLAG = "manual_flag"


class AlertStatus(Enum):
    """Status of quality alert."""
    PENDING = "pending"
    REVIEWED = "reviewed"
    DISMISSED = "dismissed"
    ESCALATED = "escalated"


class ReviewStatus(Enum):
    """Review status of validation result."""
    PENDING = "pending"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"


class QualityRule(Base):
    """Configurable quality validation rules per position and source.
    
    Supports dynamic threshold configuration for outlier detection,
    range validation, change detection, and completeness checks.
    """
    __tablename__ = "quality_rules"
    
    rule_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        nullable=False,
    )
    rule_name = Column(String(255), nullable=False, unique=True)
    rule_type = Column(String(50), nullable=False)  # outlier_detection, grade_range, etc.
    
    # Scoping
    grade_source = Column(String(50), nullable=True)  # "pff", "espn", "nfl", "yahoo" or NULL
    position = Column(String(50), nullable=True)      # "QB", "EDGE", etc. or NULL for all
    
    # Threshold configuration
    threshold_type = Column(String(50), nullable=False)  # std_dev, percentage, absolute, range
    threshold_value = Column(Float, nullable=False)      # e.g., 2.0 for 2σ, 20.0 for 20%
    
    # Execution
    severity = Column(String(50), nullable=False)  # info, warning, critical
    enabled = Column(Boolean, default=True, nullable=False)
    
    # Metadata
    description = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    quality_alerts = relationship(
        "QualityAlert",
        back_populates="rule",
        cascade="all, delete-orphan",
    )
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("rule_name", "position", "grade_source", name="uq_rule_position_source"),
        Index("idx_rule_enabled_type", "enabled", "rule_type"),
        Index("idx_rule_position_source", "position", "grade_source"),
    )
    
    def __repr__(self) -> str:
        return (
            f"<QualityRule {self.rule_name} "
            f"(type={self.rule_type}, position={self.position}, threshold={self.threshold_value})>"
        )


class QualityAlert(Base):
    """Quality alert generated when rules violated.
    
    Tracks all quality violations with audit trail for review workflow,
    escalation tracking, and historical analysis.
    """
    __tablename__ = "quality_alerts"
    
    alert_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        nullable=False,
    )
    prospect_id = Column(
        UUID(as_uuid=True),
        ForeignKey("prospects.prospect_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rule_id = Column(
        UUID(as_uuid=True),
        ForeignKey("quality_rules.rule_id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    
    # Alert details
    alert_type = Column(String(50), nullable=False)  # outlier, grade_change, etc.
    severity = Column(String(50), nullable=False)    # info, warning, critical
    
    # What triggered the alert
    grade_source = Column(String(50), nullable=True)  # pff, espn, etc.
    field_name = Column(String(255), nullable=True)   # grade_overall, grade_change, etc.
    field_value = Column(String(255), nullable=True)  # Actual value that triggered
    expected_value = Column(String(255), nullable=True)  # Expected value if applicable
    
    # Review workflow
    review_status = Column(
        String(50),
        default=ReviewStatus.PENDING.value,
        nullable=False,
    )
    reviewed_by = Column(String(255), nullable=True)  # Username or system
    reviewed_at = Column(DateTime, nullable=True)
    review_notes = Column(String(1000), nullable=True)
    
    # Escalation
    escalated_at = Column(DateTime, nullable=True)
    escalation_reason = Column(String(500), nullable=True)
    
    # Alert metadata
    alert_metadata = Column(String(2000), nullable=True)  # JSON string with details
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    prospect = relationship("Prospect", back_populates="quality_alerts")
    rule = relationship("QualityRule", back_populates="quality_alerts")
    
    # Indexes
    __table_args__ = (
        Index("idx_alert_prospect_created", "prospect_id", "created_at"),
        Index("idx_alert_severity", "severity"),
        Index("idx_alert_review_status", "review_status"),
        Index("idx_alert_grade_source", "grade_source"),
    )
    
    def __repr__(self) -> str:
        return (
            f"<QualityAlert {self.alert_id} "
            f"(prospect={self.prospect_id}, type={self.alert_type}, severity={self.severity})>"
        )


class GradeHistory(Base):
    """Daily snapshot of prospect grades for trend analysis.
    
    Tracks all grade changes day-over-day to enable change detection,
    trend analysis, and historical audit trail.
    """
    __tablename__ = "grade_history"
    
    history_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        nullable=False,
    )
    prospect_id = Column(
        UUID(as_uuid=True),
        ForeignKey("prospects.prospect_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Grade information
    grade_source = Column(String(50), nullable=False)     # pff, espn, nfl, yahoo
    grade_date = Column(DateTime, nullable=False)         # When grade was recorded
    grade_overall_raw = Column(Float, nullable=False)     # Raw grade value
    grade_overall_normalized = Column(Float, nullable=True)  # Normalized to 5.0-10.0 if applicable
    
    # Change tracking
    prior_grade = Column(Float, nullable=True)            # Previous day's grade
    grade_change = Column(Float, nullable=True)           # Difference from prior
    change_percentage = Column(Float, nullable=True)      # Percent change
    
    # Outlier detection
    is_outlier = Column(Boolean, default=False, nullable=False)
    outlier_type = Column(String(50), nullable=True)      # z_score, suspicious_change, etc.
    std_dev_from_mean = Column(Float, nullable=True)      # How many std devs from mean
    position_mean = Column(Float, nullable=True)          # Position mean at time
    position_stdev = Column(Float, nullable=True)         # Position stdev at time
    
    # Metadata
    note = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    prospect = relationship("Prospect", back_populates="grade_history")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "prospect_id", "grade_source", "grade_date",
            name="uq_grade_history_prospect_source_date"
        ),
        Index("idx_grade_history_prospect_date", "prospect_id", "grade_date"),
        Index("idx_grade_history_source_date", "grade_source", "grade_date"),
        Index("idx_grade_history_outlier", "is_outlier"),
    )
    
    def __repr__(self) -> str:
        return (
            f"<GradeHistory {self.history_id} "
            f"(prospect={self.prospect_id}, source={self.grade_source}, "
            f"date={self.grade_date.date()}, grade={self.grade_overall_raw})>"
        )


class QualityMetric(Base):
    """Summary quality metrics for dashboard and reporting.
    
    Aggregated daily statistics on grade coverage, outlier detection,
    alert generation, and overall quality score by position group.
    """
    __tablename__ = "quality_metrics"
    
    metric_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        nullable=False,
    )
    
    # Time dimension
    metric_date = Column(DateTime, nullable=False, index=True)
    
    # Dimension slicing
    position = Column(String(50), nullable=True)  # NULL = all positions
    grade_source = Column(String(50), nullable=True)  # NULL = all sources
    
    # Coverage metrics
    total_prospects = Column(Integer, default=0, nullable=False)
    prospects_with_grades = Column(Integer, default=0, nullable=False)
    coverage_percentage = Column(Float, nullable=False)  # 0-100
    
    # Quality metrics
    total_grades_loaded = Column(Integer, default=0, nullable=False)
    grades_validated = Column(Integer, default=0, nullable=False)
    validation_percentage = Column(Float, nullable=False)  # 0-100
    
    # Outlier metrics
    outliers_detected = Column(Integer, default=0, nullable=False)
    outlier_percentage = Column(Float, nullable=False)  # % of validated grades
    critical_outliers = Column(Integer, default=0, nullable=False)
    
    # Alert metrics
    alerts_generated = Column(Integer, default=0, nullable=False)
    alerts_reviewed = Column(Integer, default=0, nullable=False)
    alerts_escalated = Column(Integer, default=0, nullable=False)
    
    # Summary quality score (0-100)
    quality_score = Column(Float, nullable=False)
    
    # Metadata
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    calculation_notes = Column(String(1000), nullable=True)
    
    # Indexes
    __table_args__ = (
        UniqueConstraint(
            "metric_date", "position", "grade_source",
            name="uq_quality_metrics_date_position_source"
        ),
        Index("idx_quality_metrics_date", "metric_date"),
        Index("idx_quality_metrics_position_date", "position", "metric_date"),
    )
    
    def __repr__(self) -> str:
        return (
            f"<QualityMetric {self.metric_id} "
            f"(date={self.metric_date.date()}, position={self.position}, "
            f"quality_score={self.quality_score:.1f})>"
        )
