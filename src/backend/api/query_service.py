"""Query service for complex prospect filtering."""

import time
import hashlib
import json
from typing import Dict, List, Tuple, Optional
from sqlalchemy import and_, or_, func
from sqlalchemy.orm import Session
from decimal import Decimal

from backend.database.models import Prospect
from backend.api.schemas import QueryFilterSchema, QueryResultSchema, ProspectResponse


class QueryService:
    """Service for executing complex prospect queries."""
    
    @staticmethod
    def _build_query_hash(filters: QueryFilterSchema) -> str:
        """Generate hash of query filters for caching."""
        filter_dict = filters.model_dump(exclude={"skip", "limit"}, exclude_none=True)
        filter_json = json.dumps(filter_dict, sort_keys=True, default=str)
        return hashlib.md5(filter_json.encode()).hexdigest()
    
    @staticmethod
    def _build_query_conditions(filters: QueryFilterSchema) -> List:
        """Build SQLAlchemy filter conditions from QueryFilterSchema."""
        conditions = []
        
        # Position filter
        if filters.position:
            conditions.append(Prospect.position == filters.position.upper())
        
        # College filter (case-insensitive partial match)
        if filters.college:
            conditions.append(Prospect.college.ilike(f"%{filters.college}%"))
        
        # Height range filter
        if filters.height:
            if filters.height.min is not None:
                conditions.append(Prospect.height >= Decimal(str(filters.height.min)))
            if filters.height.max is not None:
                conditions.append(Prospect.height <= Decimal(str(filters.height.max)))
        
        # Weight range filter
        if filters.weight:
            if filters.weight.min is not None:
                conditions.append(Prospect.weight >= int(filters.weight.min))
            if filters.weight.max is not None:
                conditions.append(Prospect.weight <= int(filters.weight.max))
        
        # Draft grade range filter
        if filters.draft_grade:
            if filters.draft_grade.min is not None:
                conditions.append(Prospect.draft_grade >= Decimal(str(filters.draft_grade.min)))
            if filters.draft_grade.max is not None:
                conditions.append(Prospect.draft_grade <= Decimal(str(filters.draft_grade.max)))
        
        # Status filter (typically "active")
        if filters.injury_status:
            conditions.append(Prospect.status.in_(filters.injury_status))
        
        return conditions
    
    @staticmethod
    def execute_query(
        db: Session,
        filters: QueryFilterSchema
    ) -> Tuple[List[Prospect], int, str, float]:
        """
        Execute complex query with filters.
        
        Args:
            db: SQLAlchemy session
            filters: Query filter criteria
        
        Returns:
            Tuple of (results, total_count, query_hash, execution_time_ms)
        """
        start_time = time.time()
        
        # Build conditions
        conditions = QueryService._build_query_conditions(filters)
        
        # Build base query
        query = db.query(Prospect)
        
        # Apply all conditions with AND logic
        if conditions:
            query = query.filter(and_(*conditions))
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination
        results = query.offset(filters.skip).limit(filters.limit).all()
        
        # Calculate execution time
        execution_time_ms = (time.time() - start_time) * 1000
        
        # Generate query hash for caching
        query_hash = QueryService._build_query_hash(filters)
        
        return results, total_count, query_hash, execution_time_ms
    
    @staticmethod
    def build_response(
        prospects: List[Prospect],
        total_count: int,
        skip: int,
        limit: int,
        query_hash: str,
        execution_time_ms: float
    ) -> QueryResultSchema:
        """Build QueryResultSchema response."""
        prospect_responses = [
            ProspectResponse.model_validate(p) for p in prospects
        ]
        
        return QueryResultSchema(
            total_count=total_count,
            returned_count=len(prospect_responses),
            skip=skip,
            limit=limit,
            prospects=prospect_responses,
            execution_time_ms=round(execution_time_ms, 2),
            query_hash=query_hash
        )
