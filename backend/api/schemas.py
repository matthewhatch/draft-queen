"""Pydantic schemas for API requests and responses."""

from typing import Optional, List, Union
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
