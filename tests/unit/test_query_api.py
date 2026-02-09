"""Unit tests for query API endpoints."""

import pytest
import os

# Set testing mode before importing anything
os.environ["TESTING"] = "true"

from sqlalchemy.orm import Session
from backend.database import db
from backend.database.models import Base, Prospect
from backend.api.schemas import QueryFilterSchema, RangeFilter, ProspectResponse
from backend.api.query_service import QueryService


@pytest.fixture
def test_session():
    """Create test database session."""
    # Setup
    Base.metadata.drop_all(db.engine)
    Base.metadata.create_all(db.engine)
    
    session = db.SessionLocal()
    
    # Add test data
    prospects = [
        Prospect(
            name="Patrick Mahomes",
            position="QB",
            college="Texas Tech",
            height=6.25,
            weight=205,
            draft_grade=9.5,
            round_projection=1,
            status="active"
        ),
        Prospect(
            name="Josh Allen",
            position="QB",
            college="Wyoming",
            height=6.37,
            weight=220,
            draft_grade=8.8,
            round_projection=1,
            status="active"
        ),
        Prospect(
            name="Derrick Henry",
            position="RB",
            college="Alabama",
            height=6.27,
            weight=247,
            draft_grade=8.9,
            round_projection=2,
            status="active"
        ),
        Prospect(
            name="Travis Kelce",
            position="TE",
            college="Cincinnati",
            height=6.27,
            weight=260,
            draft_grade=7.5,
            round_projection=3,
            status="active"
        ),
        Prospect(
            name="Injury Player",
            position="WR",
            college="Georgia",
            height=6.10,
            weight=190,
            draft_grade=6.5,
            round_projection=5,
            status="injured"
        ),
    ]
    
    session.add_all(prospects)
    session.commit()
    
    yield session
    
    # Teardown
    session.close()
    Base.metadata.drop_all(db.engine)


class TestQueryService:
    """Tests for prospect query service."""
    
    def test_query_all_prospects(self, test_session):
        """Test querying all prospects."""
        filters = QueryFilterSchema(skip=0, limit=100)
        prospects, total_count, query_hash, execution_time = QueryService.execute_query(
            test_session, filters
        )
        
        assert total_count == 5
        assert len(prospects) == 5
        assert execution_time > 0
        assert len(query_hash) == 32  # MD5 hash length
    
    def test_query_by_position(self, test_session):
        """Test filtering by position."""
        filters = QueryFilterSchema(position="QB", skip=0, limit=100)
        prospects, total_count, query_hash, execution_time = QueryService.execute_query(
            test_session, filters
        )
        
        assert total_count == 2  # 2 QBs
        assert all(p.position == "QB" for p in prospects)
    
    def test_query_by_college(self, test_session):
        """Test filtering by college."""
        filters = QueryFilterSchema(college="Alabama", skip=0, limit=100)
        prospects, total_count, query_hash, execution_time = QueryService.execute_query(
            test_session, filters
        )
        
        assert total_count == 1
        assert prospects[0].name == "Derrick Henry"
    
    def test_query_by_height_range(self, test_session):
        """Test filtering by height range."""
        filters = QueryFilterSchema(
            height=RangeFilter(min=6.25, max=6.26),
            skip=0,
            limit=100
        )
        prospects, total_count, query_hash, execution_time = QueryService.execute_query(
            test_session, filters
        )
        
        assert total_count == 1
        assert prospects[0].name == "Patrick Mahomes"
    
    def test_query_by_weight_range(self, test_session):
        """Test filtering by weight range."""
        filters = QueryFilterSchema(
            weight=RangeFilter(min=240, max=250),
            skip=0,
            limit=100
        )
        prospects, total_count, query_hash, execution_time = QueryService.execute_query(
            test_session, filters
        )
        
        assert total_count == 1
        assert prospects[0].name == "Derrick Henry"
    
    def test_query_complex_filters(self, test_session):
        """Test complex query with multiple filters."""
        filters = QueryFilterSchema(
            position="QB",
            height=RangeFilter(min=6.20, max=6.40),
            weight=RangeFilter(min=200, max=230),
            draft_grade=RangeFilter(min=8.0, max=10.0),
            skip=0,
            limit=100
        )
        prospects, total_count, query_hash, execution_time = QueryService.execute_query(
            test_session, filters
        )
        
        assert total_count == 2  # Both QBs match
        assert all(p.position == "QB" for p in prospects)
    
    def test_query_by_status(self, test_session):
        """Test filtering by status."""
        filters = QueryFilterSchema(
            injury_status=["active"],
            skip=0,
            limit=100
        )
        prospects, total_count, query_hash, execution_time = QueryService.execute_query(
            test_session, filters
        )
        
        assert all(p.status == "active" for p in prospects)
    
    def test_query_pagination(self, test_session):
        """Test pagination parameters."""
        # First page
        filters1 = QueryFilterSchema(skip=0, limit=2)
        prospects1, _, _, _ = QueryService.execute_query(test_session, filters1)
        first_page_names = {p.name for p in prospects1}
        assert len(first_page_names) == 2
        
        # Second page
        filters2 = QueryFilterSchema(skip=2, limit=2)
        prospects2, _, _, _ = QueryService.execute_query(test_session, filters2)
        second_page_names = {p.name for p in prospects2}
        
        # Should have different prospects
        assert len(first_page_names & second_page_names) == 0
    
    def test_query_response_includes_hash(self, test_session):
        """Test that query response includes hash for caching."""
        filters = QueryFilterSchema(position="QB", skip=0, limit=100)
        prospects, total_count, query_hash, execution_time = QueryService.execute_query(
            test_session, filters
        )
        
        assert query_hash is not None
        assert isinstance(query_hash, str)
        assert len(query_hash) == 32  # MD5 hash
    
    def test_query_response_includes_timing(self, test_session):
        """Test that query response includes execution time."""
        filters = QueryFilterSchema(skip=0, limit=100)
        prospects, total_count, query_hash, execution_time = QueryService.execute_query(
            test_session, filters
        )
        
        assert execution_time >= 0
        assert execution_time < 1000  # Should be fast
    
    def test_query_no_matches(self, test_session):
        """Test query with no matches."""
        filters = QueryFilterSchema(position="K", skip=0, limit=100)  # No kickers
        prospects, total_count, query_hash, execution_time = QueryService.execute_query(
            test_session, filters
        )
        
        assert total_count == 0
        assert len(prospects) == 0
    
    def test_build_response_schema(self, test_session):
        """Test building response schema."""
        filters = QueryFilterSchema(skip=0, limit=2)
        prospects, total_count, query_hash, execution_time = QueryService.execute_query(
            test_session, filters
        )
        
        response = QueryService.build_response(
            prospects=prospects,
            total_count=total_count,
            skip=filters.skip,
            limit=filters.limit,
            query_hash=query_hash,
            execution_time_ms=execution_time
        )
        
        assert response.total_count == total_count
        assert response.returned_count == len(prospects)
        assert response.skip == 0
        assert response.limit == 2
        assert len(response.prospects) <= 2
