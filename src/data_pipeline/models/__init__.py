"""Pydantic models for data validation."""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class ProspectDataSchema(BaseModel):
    """Schema for prospect data validation (US-005)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    # Required Fields
    name: str = Field(..., min_length=1, max_length=255)
    position: str = Field(..., description="QB, RB, WR, TE, OL, DL, LB, DB, etc")
    college: str = Field(..., min_length=1, max_length=255)

    # Physical Attributes
    height: Optional[float] = Field(None, ge=5.5, le=7.0, description="Height in feet")
    weight: Optional[int] = Field(None, ge=150, le=350, description="Weight in lbs")
    arm_length: Optional[float] = Field(None, description="Arm length in inches")
    hand_size: Optional[float] = Field(None, description="Hand size in inches")

    # Draft Info
    draft_grade: Optional[float] = Field(None, ge=5.0, le=10.0)
    round_projection: Optional[int] = Field(None, ge=1, le=7)
    grade_source: Optional[str] = Field(None, max_length=100)

    # Status
    status: Optional[str] = Field("active", max_length=50)

    # Metadata
    data_source: Optional[str] = Field("nfl.com", max_length=100)
    source_row_id: Optional[str] = Field(None, max_length=255)

    @field_validator("position", mode="before")
    @classmethod
    def validate_position(cls, v):
        """Validate position is one of allowed values."""
        valid_positions = {"QB", "RB", "FB", "WR", "TE", "OL", "DL", "EDGE", "LB", "DB", "K", "P"}
        if v.upper() not in valid_positions:
            raise ValueError(f"Position must be one of {valid_positions}")
        return v.upper()

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, v):
        """Validate name is not empty."""
        if not v or not str(v).strip():
            raise ValueError("Name cannot be empty")
        return str(v).strip()

    @field_validator("college", mode="before")
    @classmethod
    def validate_college(cls, v):
        """Validate college is not empty."""
        if not v or not str(v).strip():
            raise ValueError("College cannot be empty")
        return str(v).strip()


class ProspectMeasurableSchema(BaseModel):
    """Schema for measurable data validation."""

    prospect_id: UUID
    forty_time: Optional[float] = Field(None, ge=4.0, le=5.5)
    bench_press_reps: Optional[int] = Field(None, ge=0)
    vertical_jump: Optional[float] = Field(None, ge=15, le=55)
    broad_jump: Optional[float] = Field(None, ge=80, le=150)
    three_cone: Optional[float] = Field(None, ge=6.0, le=9.0)
    shuttle: Optional[float] = Field(None, ge=3.8, le=5.5)
    test_type: Optional[str] = Field(None, max_length=50)
    test_date: Optional[datetime] = None


class ProspectStatsSchema(BaseModel):
    """Schema for college statistics validation."""

    prospect_id: UUID
    season: int = Field(..., ge=2000, le=2030)
    college: Optional[str] = Field(None, max_length=255)
    games_played: Optional[int] = Field(None, ge=0)
    games_started: Optional[int] = Field(None, ge=0)
    passing_yards: Optional[int] = Field(None, ge=0)
    passing_touchdowns: Optional[int] = Field(None, ge=0)
    interceptions: Optional[int] = Field(None, ge=0)
    rushing_yards: Optional[int] = Field(None, ge=0)
    rushing_touchdowns: Optional[int] = Field(None, ge=0)
    receptions: Optional[int] = Field(None, ge=0)
    receiving_yards: Optional[int] = Field(None, ge=0)
    receiving_touchdowns: Optional[int] = Field(None, ge=0)
    tackles: Optional[int] = Field(None, ge=0)
    sacks: Optional[float] = Field(None, ge=0)
    forced_fumbles: Optional[int] = Field(None, ge=0)
    interceptions_def: Optional[int] = Field(None, ge=0)
    pass_breakups: Optional[int] = Field(None, ge=0)


class ProspectInjurySchema(BaseModel):
    """Schema for injury data validation."""

    prospect_id: UUID
    injury_type: Optional[str] = Field(None, max_length=100)
    injured_body_part: Optional[str] = Field(None, max_length=100)
    injury_date: Optional[datetime] = None
    recovery_status: Optional[str] = Field(None, max_length=50)
    recovery_time_days: Optional[int] = Field(None, ge=0)
    notes: Optional[str] = None
    source: Optional[str] = Field(None, max_length=100)


class ProspectRankingSchema(BaseModel):
    """Schema for ranking data validation."""

    prospect_id: UUID
    source: str = Field(..., max_length=100)
    grader_name: Optional[str] = Field(None, max_length=255)
    grade: Optional[float] = Field(None, ge=5.0, le=10.0)
    tier: Optional[str] = Field(None, max_length=50)
    position_rank: Optional[int] = None
    overall_rank: Optional[int] = None
    ranking_date: Optional[datetime] = None
    confidence_level: Optional[str] = Field(None, max_length=50)


class DataLoadAuditSchema(BaseModel):
    """Schema for load audit records."""

    data_source: str
    total_records_received: int
    records_validated: int
    records_inserted: int
    records_updated: int
    records_skipped: int
    records_failed: int
    duration_seconds: float
    status: str
    error_summary: Optional[str] = None
    error_details: Optional[dict] = None
    operator: str = "scheduler"


class DataQualityMetricSchema(BaseModel):
    """Schema for quality metrics."""

    metric_date: datetime
    metric_name: str
    total_records: int
    metric_value: float
    threshold_lower: Optional[float] = None
    threshold_upper: Optional[float] = None
    status: str  # pass, warning, fail
    details: Optional[dict] = None


# Read-only schemas for responses
class ProspectResponseSchema(BaseModel):
    """Response schema for prospect queries."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    position: str
    college: str
    height: Optional[float]
    weight: Optional[int]
    draft_grade: Optional[float]
    round_projection: Optional[int]
    created_at: datetime
