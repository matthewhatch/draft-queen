"""SQLAlchemy models for the NFL Draft Analysis Platform."""

from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Boolean, ForeignKey, 
    Numeric, Text, JSON, Index, UniqueConstraint, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import uuid

Base = declarative_base()


class Prospect(Base):
    """Main prospects table."""
    
    __tablename__ = "prospects"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Basic Information
    name = Column(String(255), nullable=False, index=True)
    position = Column(String(10), nullable=False, index=True)
    college = Column(String(255), nullable=False, index=True)
    
    # Physical Attributes
    height = Column(Numeric(4, 2))  # feet
    weight = Column(Integer)  # lbs
    arm_length = Column(Numeric(4, 2))
    hand_size = Column(Numeric(4, 2))
    
    # Draft Information
    draft_grade = Column(Numeric(3, 1))  # 5.0 to 10.0
    round_projection = Column(Integer)
    grade_source = Column(String(100))
    
    # Status
    status = Column(String(50), default="active", index=True)
    
    # Audit Columns
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(100), default="system")
    updated_by = Column(String(100), default="system")
    data_source = Column(String(100), default="nfl.com")
    
    # Relationships
    measurables = relationship("ProspectMeasurable", back_populates="prospect", cascade="all, delete-orphan")
    stats = relationship("ProspectStats", back_populates="prospect", cascade="all, delete-orphan")
    injuries = relationship("ProspectInjury", back_populates="prospect", cascade="all, delete-orphan")
    rankings = relationship("ProspectRanking", back_populates="prospect", cascade="all, delete-orphan")
    grades = relationship("ProspectGrade", back_populates="prospect", cascade="all, delete-orphan")
    quality_alerts = relationship("QualityAlert", back_populates="prospect", cascade="all, delete-orphan")
    grade_history = relationship("GradeHistory", back_populates="prospect", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("name", "position", "college", name="idx_prospect_unique"),
        CheckConstraint("position IN ('QB', 'RB', 'FB', 'WR', 'TE', 'OL', 'DL', 'EDGE', 'LB', 'DB', 'K', 'P')", name="ck_valid_position"),
        CheckConstraint("height BETWEEN 5.5 AND 7.0", name="ck_valid_height"),
        CheckConstraint("weight BETWEEN 150 AND 350", name="ck_valid_weight"),
        CheckConstraint("draft_grade BETWEEN 5.0 AND 10.0", name="ck_valid_draft_grade"),
    )


class ProspectMeasurable(Base):
    """Prospect physical measurables (test results)."""
    
    __tablename__ = "prospect_measurables"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prospect_id = Column(UUID(as_uuid=True), ForeignKey("prospects.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Test Results
    forty_time = Column(Numeric(4, 3))  # seconds
    bench_press_reps = Column(Integer)
    vertical_jump = Column(Numeric(4, 2))  # inches
    broad_jump = Column(Numeric(5, 2))  # inches
    three_cone = Column(Numeric(4, 3))  # seconds
    shuttle = Column(Numeric(4, 3))  # seconds
    
    # Test Information
    test_type = Column(String(50))  # combine, pro_day, other
    test_date = Column(DateTime)
    
    # Audit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    prospect = relationship("Prospect", back_populates="measurables")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("forty_time IS NULL OR forty_time BETWEEN 4.0 AND 5.5", name="ck_valid_forty"),
        CheckConstraint("vertical_jump IS NULL OR vertical_jump BETWEEN 15 AND 55", name="ck_valid_vertical"),
        CheckConstraint("broad_jump IS NULL OR broad_jump BETWEEN 80 AND 150", name="ck_valid_broad"),
        Index("idx_measurables_prospect_id", "prospect_id"),
        Index("idx_measurables_test_date", "test_date"),
    )


class ProspectStats(Base):
    """College performance statistics."""
    
    __tablename__ = "prospect_stats"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prospect_id = Column(UUID(as_uuid=True), ForeignKey("prospects.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Season
    season = Column(Integer, nullable=False, index=True)
    college = Column(String(255))
    
    # Games
    games_played = Column(Integer)
    games_started = Column(Integer)
    
    # Offensive Stats
    passing_yards = Column(Integer)
    passing_touchdowns = Column(Integer)
    interceptions = Column(Integer)
    rushing_yards = Column(Integer)
    rushing_touchdowns = Column(Integer)
    receptions = Column(Integer)
    receiving_yards = Column(Integer)
    receiving_touchdowns = Column(Integer)
    
    # Defensive Stats
    tackles = Column(Integer)
    sacks = Column(Numeric(5, 2))
    forced_fumbles = Column(Integer)
    interceptions_def = Column(Integer)
    pass_breakups = Column(Integer)
    
    # Audit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    prospect = relationship("Prospect", back_populates="stats")
    
    __table_args__ = (
        Index("idx_stats_prospect_id", "prospect_id"),
        Index("idx_stats_season", "season"),
    )

class ProspectGrade(Base):
    """Prospect grades from various sources (PFF, ESPN, etc.)."""
    
    __tablename__ = "prospect_grades"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    prospect_id = Column(UUID(as_uuid=True), ForeignKey("prospects.id", ondelete="CASCADE"), nullable=False, index=True)
    source = Column(String(50), nullable=False, index=True)          # "pff", "espn", "nfl", etc.
    grade_overall = Column(Float, nullable=True)                      # PFF 0–100 scale (store raw)
    grade_normalized = Column(Float, nullable=True)                   # Normalized to 5.0–10.0 scale
    grade_position = Column(String(10), nullable=True)                # Position at time of grading (PFF-native, e.g. "LT")
    match_confidence = Column(Float, nullable=True)                   # Fuzzy-match score 0–100
    grade_date = Column(DateTime, nullable=True)                      # Date grade was issued
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(50), default="pff_loader")
    
    # Relationship back to Prospect
    prospect = relationship("Prospect", back_populates="grades")
    
    __table_args__ = (
        UniqueConstraint("prospect_id", "source", "grade_date", name="uq_prospect_grade_source_date"),
        Index("idx_grade_source", "source"),
        Index("idx_grade_prospect", "prospect_id"),
    )

class ProspectInjury(Base):
    """Injury history."""
    
    __tablename__ = "prospect_injuries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prospect_id = Column(UUID(as_uuid=True), ForeignKey("prospects.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Details
    injury_type = Column(String(100))
    injured_body_part = Column(String(100))
    injury_date = Column(DateTime)
    recovery_status = Column(String(50))  # healed, recovering, chronic, unknown
    recovery_time_days = Column(Integer)
    
    # Additional Info
    notes = Column(Text)
    source = Column(String(100))
    
    # Audit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    prospect = relationship("Prospect", back_populates="injuries")
    
    __table_args__ = (
        Index("idx_injuries_prospect_id", "prospect_id"),
        Index("idx_injuries_injury_type", "injury_type"),
    )


class ProspectRanking(Base):
    """Rankings from multiple sources."""
    
    __tablename__ = "prospect_rankings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prospect_id = Column(UUID(as_uuid=True), ForeignKey("prospects.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Source
    source = Column(String(100), nullable=False, index=True)
    grader_name = Column(String(255))
    
    # Grade
    grade = Column(Numeric(3, 1))  # 5.0 to 10.0
    tier = Column(String(50))  # 1st round, 2nd round, etc
    position_rank = Column(Integer)
    overall_rank = Column(Integer)
    
    # Date
    ranking_date = Column(DateTime, index=True)
    
    # Confidence
    confidence_level = Column(String(50))  # high, medium, low
    
    # Audit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    prospect = relationship("Prospect", back_populates="rankings")
    
    __table_args__ = (
        Index("idx_rankings_prospect_id", "prospect_id"),
        Index("idx_rankings_source", "source"),
        Index("idx_rankings_date", "ranking_date"),
    )


class StagingProspect(Base):
    """Staging table for data validation."""
    
    __tablename__ = "staging_prospects"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Data
    name = Column(String(255))
    position = Column(String(10))
    college = Column(String(255))
    height = Column(Numeric(4, 2))
    weight = Column(Integer)
    draft_grade = Column(Numeric(3, 1))
    round_projection = Column(Integer)
    
    # Validation
    validation_status = Column(String(50), index=True)  # pending, validated, failed
    validation_errors = Column(JSON)
    
    # Load Info
    load_id = Column(UUID(as_uuid=True), index=True)
    source_row_id = Column(String(255))
    
    # Audit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    data_source = Column(String(100))
    
    __table_args__ = (
        Index("idx_staging_validation_status", "validation_status"),
        Index("idx_staging_load_id", "load_id"),
    )


class DataLoadAudit(Base):
    """Audit trail for data loads."""
    
    __tablename__ = "data_load_audit"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Load Info
    load_date = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    data_source = Column(String(100), nullable=False, index=True)
    
    # Counts
    total_records_received = Column(Integer)
    records_validated = Column(Integer)
    records_inserted = Column(Integer)
    records_updated = Column(Integer)
    records_skipped = Column(Integer)
    records_failed = Column(Integer)
    
    # Performance
    duration_seconds = Column(Numeric(6, 2))
    
    # Status
    status = Column(String(50), index=True)  # success, partial, failed
    error_summary = Column(Text)
    error_details = Column(JSON)
    
    # Operator
    operator = Column(String(100), default="scheduler")
    
    # Audit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index("idx_load_audit_date", "load_date"),
        Index("idx_load_audit_source", "data_source"),
        Index("idx_load_audit_status", "status"),
    )


class DataQualityMetric(Base):
    """Data quality metrics tracking."""
    
    __tablename__ = "data_quality_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Metric
    metric_date = Column(DateTime, nullable=False, index=True)
    metric_time = Column(DateTime, default=datetime.utcnow)
    metric_name = Column(String(100), nullable=False, index=True)
    
    # Values
    total_records = Column(Integer)
    metric_value = Column(Numeric(10, 4))
    threshold_lower = Column(Numeric(10, 4))
    threshold_upper = Column(Numeric(10, 4))
    
    # Status
    status = Column(String(50), index=True)  # pass, warning, fail
    details = Column(JSON)
    
    # Audit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index("idx_quality_metrics_date", "metric_date"),
        Index("idx_quality_metrics_name", "metric_name"),
        Index("idx_quality_metrics_status", "status"),
    )


class DataQualityReport(Base):
    """Daily quality reports."""
    
    __tablename__ = "data_quality_report"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Report
    report_date = Column(DateTime, nullable=False, index=True)
    report_generated_at = Column(DateTime, default=datetime.utcnow)
    
    # Counts
    total_prospects = Column(Integer)
    new_prospects_today = Column(Integer)
    updated_prospects_today = Column(Integer)
    
    # Quality
    completeness_pct = Column(Numeric(5, 2))
    missing_required_fields_count = Column(Integer)
    duplicate_records = Column(Integer)
    outlier_records = Column(Integer)
    validation_errors = Column(Integer)
    
    # Coverage
    records_with_measurables = Column(Integer)
    records_with_stats = Column(Integer)
    records_with_rankings = Column(Integer)
    
    # Freshness
    oldest_record_days_ago = Column(Integer)
    newest_record_today_count = Column(Integer)
    
    # Alerts
    has_alerts = Column(Boolean)
    alert_summary = Column(Text)
    alert_details = Column(JSON)
    
    # Audit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index("idx_quality_report_date", "report_date"),
    )


# Note: data_pipeline models are imported elsewhere to avoid circular imports
# ProspectGrade, QualityRule, QualityAlert, GradeHistory, QualityMetric
# are defined in data_pipeline.models.* and imported when needed
