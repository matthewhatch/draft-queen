"""FastAPI routes for prospect queries."""

from fastapi import APIRouter, Depends, Query, HTTPException, Body, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import logging
from datetime import datetime
from typing import Optional

from backend.database import db
from backend.api.schemas import QueryFilterSchema, QueryResultSchema, RangeFilter, ExportRequest, ExportResponse
from backend.api.query_service import QueryService
from backend.api.export_service import ExportService, ExportFormat

logger = logging.getLogger(__name__)

# Create router
query_router = APIRouter(prefix="/api/prospects", tags=["prospects"])
export_router = APIRouter(prefix="/api/exports", tags=["exports"])


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


@export_router.post(
    "/",
    summary="Export prospects",
    description="Export prospects to JSON, JSONL, CSV, or Parquet format"
)
async def export_prospects(
    request: ExportRequest = Body(..., example={
        "format": "json",
        "filters": {
            "position": "QB",
            "college": "Alabama"
        },
        "pretty": True
    }),
    session: Session = Depends(db.get_session)
) -> Response:
    """Export prospects in specified format."""
    try:
        # Validate format
        try:
            export_format = ExportFormat(request.format.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported format. Supported: json, jsonl, csv, parquet"
            )
        
        logger.info(
            f"Export request: format={export_format.value}, "
            f"filters={'yes' if request.filters else 'no'}"
        )
        
        # Generate export
        exported_data = ExportService.export_to_format(
            session,
            export_format,
            request.filters,
            request.pretty
        )
        
        # Generate filename
        timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H%M%S")
        file_extension = ExportService.get_file_extension(export_format)
        filename = f"prospects_{timestamp}.{file_extension}"
        media_type = ExportService.get_content_type(export_format)
        
        logger.info(f"Export successful: {filename}")
        
        # Return response
        if isinstance(exported_data, bytes):
            return Response(
                content=exported_data,
                media_type=media_type,
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"'
                }
            )
        else:
            return Response(
                content=exported_data,
                media_type=media_type,
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"'
                }
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Export failed: {str(e)}"
        )


@export_router.get(
    "/{format_name}",
    summary="Quick export",
    description="Quick export without request body"
)
async def quick_export(
    format_name: str = Query(..., description="Export format: json, jsonl, csv, parquet"),
    position: Optional[str] = Query(None, description="Filter by position"),
    college: Optional[str] = Query(None, description="Filter by college"),
    skip: int = Query(0, ge=0, description="Records to skip"),
    limit: int = Query(1000, ge=1, le=10000, description="Records to return"),
    session: Session = Depends(db.get_session)
) -> Response:
    """Quick export using URL query parameters."""
    try:
        # Validate format
        try:
            export_format = ExportFormat(format_name.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported format. Supported: json, jsonl, csv, parquet"
            )
        
        # Build filters
        filters = QueryFilterSchema(
            position=position,
            college=college,
            skip=skip,
            limit=limit
        )
        
        # Generate export
        exported_data = ExportService.export_to_format(
            session,
            export_format,
            filters,
            pretty=True
        )
        
        # Generate filename
        timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H%M%S")
        file_extension = ExportService.get_file_extension(export_format)
        filename = f"prospects_{timestamp}.{file_extension}"
        media_type = ExportService.get_content_type(export_format)
        
        # Return response
        if isinstance(exported_data, bytes):
            return Response(
                content=exported_data,
                media_type=media_type,
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"'
                }
            )
        else:
            return Response(
                content=exported_data,
                media_type=media_type,
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"'
                }
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Export failed: {str(e)}"
        )
