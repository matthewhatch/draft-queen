"""Pydantic schemas for API requests and responses."""

from typing import Optional, List, Union, Dict
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from decimal import Decimal
from uuid import UUID


class RangeFilter(BaseModel):
    """Range filter for numeric values."""
    min: Optional[float] = Field(None, description="Minimum value (inclusive)")
    max: Optional[float] = Field(None, description="Maximum value (inclusive)")


class QueryFilterSchema(BaseModel):
    """Schema for complex prospect queries."""
    
    position: Optional[str] = Field(None, description="Position code (e.g., 'QB', 'RB', 'WR')")
    college: Optional[str] = Field(None, description="College name (partial match supported)")
    height: Optional[RangeFilter] = Field(None, description="Height range in feet (e.g., 6.0-6.5)")
    weight: Optional[RangeFilter] = Field(None, description="Weight range in lbs")
    forty_time: Optional[RangeFilter] = Field(None, description="40-yard dash time in seconds")
    draft_grade: Optional[RangeFilter] = Field(None, description="Draft grade range (5.0-10.0)")
    injury_status: Optional[List[str]] = Field(None, description="Filter by injury status (e.g., ['healthy', 'minor_injury'])")
    skip: int = Field(0, ge=0, description="Number of records to skip")
    limit: int = Field(100, ge=1, le=500, description="Maximum records to return")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "position": "QB",
            "college": "Alabama",
            "height": {"min": 6.0, "max": 6.5},
            "weight": {"min": 200, "max": 230},
            "forty_time": {"min": 4.3, "max": 5.0},
            "draft_grade": {"min": 7.0, "max": 10.0},
            "injury_status": ["healthy"],
            "skip": 0,
            "limit": 50
        }
    })


class ProspectResponse(BaseModel):
    """Schema for prospect response."""
    
    id: Union[str, UUID] = Field(description="Prospect ID")
    name: str
    position: str
    college: str
    height: Optional[float] = None
    weight: Optional[int] = None
    draft_grade: Optional[float] = None
    round_projection: Optional[int] = None
    status: str
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class QueryResultSchema(BaseModel):
    """Schema for query results."""
    
    total_count: int = Field(description="Total matching records")
    returned_count: int = Field(description="Number of records in this response")
    skip: int = Field(description="Records skipped")
    limit: int = Field(description="Requested limit")
    prospects: List[ProspectResponse] = Field(description="Matching prospect records")
    execution_time_ms: float = Field(description="Query execution time in milliseconds")
    query_hash: str = Field(description="Hash of query for caching purposes")


class QuerySaveSchema(BaseModel):
    """Schema for saving a query for reuse."""
    
    name: str = Field(description="Friendly name for saved query")
    description: Optional[str] = Field(None, description="Description of query")
    filters: QueryFilterSchema = Field(description="Filter criteria")


class SavedQueryResponse(BaseModel):
    """Schema for saved query response."""
    
    id: str
    name: str
    description: Optional[str]
    filters: QueryFilterSchema
    created_at: datetime
    run_count: int = Field(default=0, description="Number of times query has been executed")
    
    model_config = ConfigDict(from_attributes=True)


class ExportRequest(BaseModel):
    """Schema for export request."""
    
    format: str = Field(
        description="Export format: json, jsonl, csv, or parquet"
    )
    filters: Optional[QueryFilterSchema] = Field(
        None,
        description="Optional query filters to apply before export"
    )
    pretty: bool = Field(
        True,
        description="Pretty-print JSON output (for json/jsonl formats)"
    )
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "format": "json",
            "filters": {
                "position": "QB",
                "college": "Alabama"
            },
            "pretty": True
        }
    })


class ExportResponse(BaseModel):
    """Schema for export response metadata."""
    
    format: str
    record_count: int
    file_size_bytes: int
    file_extension: str
    content_type: str
    created_at: datetime
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "format": "json",
            "record_count": 42,
            "file_size_bytes": 12847,
            "file_extension": "json",
            "content_type": "application/json",
            "created_at": "2026-02-09T12:00:00Z"
        }
    })


class FieldStatistics(BaseModel):
    """Statistics for a single field."""
    unit: str = Field(description="Unit of measurement")
    count: int = Field(description="Number of non-null values")
    min: float = Field(description="Minimum value")
    max: float = Field(description="Maximum value")
    average: float = Field(description="Average value")
    median: float = Field(description="Median value (50th percentile)")
    percentile_25: float = Field(description="25th percentile")
    percentile_75: float = Field(description="75th percentile")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "unit": "lbs",
            "count": 8,
            "min": 180.0,
            "max": 320.0,
            "average": 245.5,
            "median": 240.0,
            "percentile_25": 210.0,
            "percentile_75": 280.0
        }
    })


class PositionStatisticsResponse(BaseModel):
    """Position statistics response."""
    position: str = Field(description="Position code (e.g., QB, RB)")
    count: int = Field(description="Number of prospects in this position")
    height: Optional[FieldStatistics] = Field(None, description="Height statistics (feet)")
    weight: Optional[FieldStatistics] = Field(None, description="Weight statistics (lbs)")
    draft_grade: Optional[FieldStatistics] = Field(None, description="Draft grade statistics")
    filters_applied: Optional[dict] = Field(None, description="Filters that were applied")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "position": "QB",
            "count": 10,
            "height": {
                "unit": "feet",
                "count": 10,
                "min": 6.0,
                "max": 6.5,
                "average": 6.25,
                "median": 6.25,
                "percentile_25": 6.1,
                "percentile_75": 6.4
            },
            "weight": {
                "unit": "lbs",
                "count": 10,
                "min": 200.0,
                "max": 240.0,
                "average": 220.0,
                "median": 220.0,
                "percentile_25": 210.0,
                "percentile_75": 230.0
            },
            "draft_grade": {
                "unit": "grade",
                "count": 10,
                "min": 7.5,
                "max": 9.5,
                "average": 8.5,
                "median": 8.5,
                "percentile_25": 8.0,
                "percentile_75": 9.0
            },
            "filters_applied": None
        }
    })


class PositionsSummaryResponse(BaseModel):
    """Summary of all positions."""
    positions: Dict[str, dict] = Field(description="Position summary data")
    total_positions: int = Field(description="Number of positions")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "positions": {
                "QB": {"count": 10, "height_avg": 6.25, "weight_avg": 220.0, "draft_grade_avg": 8.5},
                "RB": {"count": 15, "height_avg": 5.9, "weight_avg": 205.0, "draft_grade_avg": 7.8}
            },
            "total_positions": 2
        }
    })

