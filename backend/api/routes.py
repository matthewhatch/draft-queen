"""FastAPI routes for prospect queries."""

from fastapi import APIRouter, Depends, Query, HTTPException, Body
from sqlalchemy.orm import Session
import logging

from backend.database import db
from backend.api.schemas import QueryFilterSchema, QueryResultSchema, RangeFilter
from backend.api.query_service import QueryService

logger = logging.getLogger(__name__)

# Create router
query_router = APIRouter(prefix="/api/prospects", tags=["prospects"])


@query_router.post(
    "/query",
    response_model=QueryResultSchema,
    summary="Execute complex prospect query",
    description="Execute a complex query with multiple filter criteria combined using AND logic"
)
async def query_prospects(
    filters: QueryFilterSchema = Body(..., example={
        "position": "QB",
        "college": "Alabama",
        "height": {"min": 6.0, "max": 6.5},
        "weight": {"min": 200, "max": 230},
        "forty_time": {"min": 4.3, "max": 5.0},
        "skip": 0,
        "limit": 50
    }),
    session: Session = Depends(db.get_session)
) -> QueryResultSchema:
    """
    Execute complex prospect query with multiple filter criteria.
    
    All filters use AND logic (must match all criteria).
    
    **Filter Examples:**
    - Position: "QB", "RB", "WR", "TE", "OL", "DL", "LB", "DB"
    - College: Partial match (case-insensitive)
    - Height/Weight/40-Time: Range with optional min and max
    - Draft Grade: Range (typically 5.0-10.0)
    - Injury Status: List of statuses to include
    
    **Response Time:**
    - Simple queries (1-2 filters): < 100ms
    - Complex queries (3+ filters): 100-500ms
    - Large result sets (pagination): < 2 seconds
    """
    try:
        logger.info(
            f"Query received: position={filters.position}, college={filters.college}, "
            f"skip={filters.skip}, limit={filters.limit}"
        )
        
        # Execute query
        prospects, total_count, query_hash, execution_time = QueryService.execute_query(
            session, filters
        )
        
        # Build response
        response = QueryService.build_response(
            prospects=prospects,
            total_count=total_count,
            skip=filters.skip,
            limit=filters.limit,
            query_hash=query_hash,
            execution_time_ms=execution_time
        )
        
        logger.info(
            f"Query executed successfully: found {total_count} records, "
            f"returned {response.returned_count}, time={execution_time:.2f}ms"
        )
        
        return response
    
    except Exception as e:
        logger.error(f"Query execution failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Query execution failed: {str(e)}"
        )


@query_router.get(
    "/",
    response_model=QueryResultSchema,
    summary="Query prospects with URL parameters",
    description="Execute query using URL query parameters (simpler than POST)"
)
async def query_prospects_simple(
    position: str = Query(None, description="Position filter"),
    college: str = Query(None, description="College filter"),
    height_min: float = Query(None, description="Minimum height in feet"),
    height_max: float = Query(None, description="Maximum height in feet"),
    weight_min: float = Query(None, description="Minimum weight in lbs"),
    weight_max: float = Query(None, description="Maximum weight in lbs"),
    draft_grade_min: float = Query(None, description="Minimum draft grade"),
    draft_grade_max: float = Query(None, description="Maximum draft grade"),
    skip: int = Query(0, ge=0, description="Records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Records to return"),
    session: Session = Depends(db.get_session)
) -> QueryResultSchema:
    """
    Execute query using URL parameters for convenience.
    
    **Example:**
    ```
    /api/prospects/?position=QB&college=Alabama&height_min=6.0&height_max=6.5
    ```
    """
    # Build filter from parameters
    filters = QueryFilterSchema(
        position=position,
        college=college,
        height=RangeFilter(min=height_min, max=height_max) if height_min or height_max else None,
        weight=RangeFilter(min=weight_min, max=weight_max) if weight_min or weight_max else None,
        draft_grade=RangeFilter(min=draft_grade_min, max=draft_grade_max) if draft_grade_min or draft_grade_max else None,
        skip=skip,
        limit=limit
    )
    
    try:
        prospects, total_count, query_hash, execution_time = QueryService.execute_query(
            session, filters
        )
        
        response = QueryService.build_response(
            prospects=prospects,
            total_count=total_count,
            skip=filters.skip,
            limit=filters.limit,
            query_hash=query_hash,
            execution_time_ms=execution_time
        )
        
        return response
    
    except Exception as e:
        logger.error(f"Query execution failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Query execution failed: {str(e)}"
        )
