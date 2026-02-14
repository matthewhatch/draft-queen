"""Pydantic schemas for quality and alert API responses."""

from typing import Optional, List, Dict, Union
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from uuid import UUID
from enum import Enum


class AlertSeverityEnum(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertTypeEnum(str, Enum):
    """Alert types."""
    LOW_COVERAGE = "low_coverage"
    LOW_VALIDATION = "low_validation"
    HIGH_OUTLIERS = "high_outliers"
    LOW_OVERALL_SCORE = "low_overall_score"
    GRADE_FRESHNESS = "grade_freshness"
    SOURCE_MISSING = "source_missing"


class AlertResponse(BaseModel):
    """Schema for individual alert response."""
    
    id: Union[str, UUID] = Field(description="Alert ID (UUID)")
    alert_type: AlertTypeEnum = Field(description="Type of alert")
    severity: AlertSeverityEnum = Field(description="Severity level")
    message: str = Field(description="Human-readable alert message")
    position: Optional[str] = Field(None, description="Position code (e.g., 'QB', 'RB')")
    grade_source: Optional[str] = Field(None, description="Grade source (e.g., 'pff', 'espn')")
    metric_value: Optional[float] = Field(None, description="Current metric value")
    threshold_value: Optional[float] = Field(None, description="Threshold that was breached")
    quality_score: Optional[float] = Field(None, description="Overall quality score")
    generated_at: datetime = Field(description="When the alert was generated")
    acknowledged: bool = Field(default=False, description="Whether alert has been acknowledged")
    acknowledged_by: Optional[str] = Field(None, description="User or system that acknowledged")
    acknowledged_at: Optional[datetime] = Field(None, description="When alert was acknowledged")
    
    model_config = ConfigDict(from_attributes=True)


class AlertListResponse(BaseModel):
    """Schema for alert list response."""
    
    total_count: int = Field(description="Total alerts matching criteria")
    returned_count: int = Field(description="Number of alerts in this response")
    alerts: List[AlertResponse] = Field(description="List of alerts")
    unacknowledged_count: int = Field(description="Count of unacknowledged alerts")
    critical_count: int = Field(description="Count of critical alerts")
    warning_count: int = Field(description="Count of warning alerts")
    info_count: int = Field(description="Count of info alerts")


class AlertSummaryResponse(BaseModel):
    """Schema for alert summary statistics."""
    
    total_alerts: int = Field(description="Total alerts in time period")
    unacknowledged_critical: int = Field(description="Unacknowledged critical alerts")
    unacknowledged_warning: int = Field(description="Unacknowledged warning alerts")
    unacknowledged_info: int = Field(description="Unacknowledged info alerts")
    
    by_position: Dict[str, int] = Field(description="Alert count by position")
    by_source: Dict[str, int] = Field(description="Alert count by grade source")
    by_type: Dict[str, int] = Field(description="Alert count by alert type")
    
    critical_positions: List[str] = Field(description="Positions with critical alerts")
    critical_sources: List[str] = Field(description="Sources with critical alerts")
    
    oldest_unacknowledged_alert_age_hours: Optional[float] = Field(
        None, 
        description="Hours since oldest unacknowledged alert"
    )


class QualityMetricsResponse(BaseModel):
    """Schema for quality metrics response."""
    
    position: Optional[str] = Field(None, description="Position code")
    grade_source: Optional[str] = Field(None, description="Grade source")
    coverage_percentage: float = Field(description="Percentage of prospects with grades")
    validation_percentage: float = Field(description="Percentage of valid grades")
    outlier_percentage: float = Field(description="Percentage of outlier grades")
    quality_score: float = Field(description="Overall quality score (0-100)")
    total_prospects: int = Field(description="Total prospects analyzed")
    prospects_with_grades: int = Field(description="Prospects with grades")
    valid_grades: int = Field(description="Valid grades count")
    outliers: int = Field(description="Detected outlier count")
    last_updated: datetime = Field(description="When metrics were last calculated")
    
    model_config = ConfigDict(from_attributes=True)


class AcknowledgeAlertRequest(BaseModel):
    """Schema for acknowledging an alert."""
    
    acknowledged_by: str = Field(description="User or system acknowledging the alert")


class BulkAcknowledgeRequest(BaseModel):
    """Schema for acknowledging multiple alerts."""
    
    alert_ids: List[Union[str, UUID]] = Field(description="List of alert IDs to acknowledge")
    acknowledged_by: str = Field(description="User or system acknowledging the alerts")


class BulkAcknowledgeResponse(BaseModel):
    """Schema for bulk acknowledge response."""
    
    acknowledged: int = Field(description="Number of successfully acknowledged alerts")
    failed: int = Field(description="Number of failed acknowledges")
    alert_ids: List[Union[str, UUID]] = Field(description="IDs of acknowledged alerts")
    failed_ids: List[Union[str, UUID]] = Field(default_factory=list, description="IDs that failed to acknowledge")


class AlertFilterParams(BaseModel):
    """Schema for alert filter parameters."""
    
    days: int = Field(default=1, ge=1, le=365, description="Number of days to look back")
    severity: Optional[AlertSeverityEnum] = Field(None, description="Filter by severity")
    acknowledged: Optional[bool] = Field(None, description="Filter by acknowledgment status")
    position: Optional[str] = Field(None, description="Filter by position")
    source: Optional[str] = Field(None, description="Filter by grade source")
    skip: int = Field(default=0, ge=0, description="Number of records to skip")
    limit: int = Field(default=50, ge=1, le=500, description="Maximum records to return")
    
    model_config = ConfigDict(from_attributes=True)


class AlertDigestResponse(BaseModel):
    """Schema for alert digest (email preview)."""
    
    subject: str = Field(description="Email subject line")
    body: str = Field(description="Email body (HTML)")
    alert_count: int = Field(description="Total alerts in digest")
    critical_count: int = Field(description="Critical alerts count")
    warning_count: int = Field(description="Warning alerts count")
    info_count: int = Field(description="Info alerts count")
    digest_date: datetime = Field(description="Date digest was generated")
    would_send_to: List[str] = Field(default_factory=list, description="Email recipients (if configured)")
