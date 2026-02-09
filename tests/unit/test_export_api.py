"""Unit tests for export API endpoints."""

import pytest
import os
import json

# Set testing mode before importing anything
os.environ["TESTING"] = "true"

from sqlalchemy.orm import Session
from backend.database import db
from backend.database.models import Base, Prospect
from backend.api.schemas import QueryFilterSchema
from backend.api.export_service import ExportService, ExportFormat


@pytest.fixture
def test_session_with_data():
    """Create test database session with sample data."""
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
    ]
    
    session.add_all(prospects)
    session.commit()
    
    yield session
    
    # Teardown
    session.close()
    Base.metadata.drop_all(db.engine)


class TestExportService:
    """Tests for export service."""
    
    def test_export_json(self, test_session_with_data):
        """Test JSON export."""
        json_str = ExportService.export_json(test_session_with_data)
        
        assert isinstance(json_str, str)
        data = json.loads(json_str)
        assert len(data) == 3
        assert data[0]["name"] == "Patrick Mahomes"
        assert data[0]["position"] == "QB"
        assert "id" in data[0]
        assert "created_at" in data[0]
    
    def test_export_json_with_filters(self, test_session_with_data):
        """Test JSON export with filters."""
        filters = QueryFilterSchema(position="QB", skip=0, limit=100)
        json_str = ExportService.export_json(test_session_with_data, filters)
        
        data = json.loads(json_str)
        assert len(data) == 2
        assert all(p["position"] == "QB" for p in data)
    
    def test_export_json_pretty(self, test_session_with_data):
        """Test pretty-printed JSON export."""
        json_str = ExportService.export_json(test_session_with_data, pretty=True)
        
        # Pretty JSON should have indentation
        assert "\n" in json_str
        assert "  " in json_str
    
    def test_export_json_compact(self, test_session_with_data):
        """Test compact JSON export."""
        json_str = ExportService.export_json(test_session_with_data, pretty=False)
        
        # Compact JSON should not have indentation
        data = json.loads(json_str)
        assert len(data) == 3
    
    def test_export_jsonl(self, test_session_with_data):
        """Test JSONL export."""
        jsonl_str = ExportService.export_jsonl(test_session_with_data)
        
        lines = jsonl_str.strip().split("\n")
        assert len(lines) == 3
        
        for line in lines:
            record = json.loads(line)
            assert "name" in record
            assert "position" in record
    
    def test_export_csv(self, test_session_with_data):
        """Test CSV export."""
        csv_str = ExportService.export_csv(test_session_with_data)
        
        assert isinstance(csv_str, str)
        lines = csv_str.strip().split("\n")
        assert len(lines) == 4  # Header + 3 data rows
        
        # Check header
        assert "name" in lines[0]
        assert "position" in lines[0]
        assert "college" in lines[0]
    
    def test_export_csv_with_filters(self, test_session_with_data):
        """Test CSV export with filters."""
        filters = QueryFilterSchema(college="Alabama", skip=0, limit=100)
        csv_str = ExportService.export_csv(test_session_with_data, filters)
        
        lines = csv_str.strip().split("\n")
        assert len(lines) == 2  # Header + 1 data row
        assert "Derrick Henry" in csv_str
    
    def test_export_parquet(self, test_session_with_data):
        """Test Parquet export."""
        parquet_bytes = ExportService.export_parquet(test_session_with_data)
        
        assert isinstance(parquet_bytes, bytes)
        assert len(parquet_bytes) > 0
        # Parquet magic number
        assert parquet_bytes.startswith(b"PAR1")
    
    def test_export_parquet_with_filters(self, test_session_with_data):
        """Test Parquet export with filters."""
        filters = QueryFilterSchema(position="RB", skip=0, limit=100)
        parquet_bytes = ExportService.export_parquet(test_session_with_data, filters)
        
        assert isinstance(parquet_bytes, bytes)
        assert parquet_bytes.startswith(b"PAR1")
    
    def test_export_to_format_json(self, test_session_with_data):
        """Test export_to_format with JSON."""
        result = ExportService.export_to_format(
            test_session_with_data,
            ExportFormat.JSON
        )
        
        assert isinstance(result, str)
        data = json.loads(result)
        assert len(data) == 3
    
    def test_export_to_format_jsonl(self, test_session_with_data):
        """Test export_to_format with JSONL."""
        result = ExportService.export_to_format(
            test_session_with_data,
            ExportFormat.JSONL
        )
        
        assert isinstance(result, str)
        lines = result.strip().split("\n")
        assert len(lines) == 3
    
    def test_export_to_format_csv(self, test_session_with_data):
        """Test export_to_format with CSV."""
        result = ExportService.export_to_format(
            test_session_with_data,
            ExportFormat.CSV
        )
        
        assert isinstance(result, str)
        lines = result.strip().split("\n")
        assert len(lines) == 4
    
    def test_export_to_format_parquet(self, test_session_with_data):
        """Test export_to_format with Parquet."""
        result = ExportService.export_to_format(
            test_session_with_data,
            ExportFormat.PARQUET
        )
        
        assert isinstance(result, bytes)
        assert result.startswith(b"PAR1")
    
    def test_get_file_extension(self):
        """Test file extension lookup."""
        assert ExportService.get_file_extension(ExportFormat.JSON) == "json"
        assert ExportService.get_file_extension(ExportFormat.JSONL) == "jsonl"
        assert ExportService.get_file_extension(ExportFormat.CSV) == "csv"
        assert ExportService.get_file_extension(ExportFormat.PARQUET) == "parquet"
    
    def test_get_content_type(self):
        """Test content type lookup."""
        assert ExportService.get_content_type(ExportFormat.JSON) == "application/json"
        assert ExportService.get_content_type(ExportFormat.JSONL) == "application/x-ndjson"
        assert ExportService.get_content_type(ExportFormat.CSV) == "text/csv"
        assert ExportService.get_content_type(ExportFormat.PARQUET) == "application/octet-stream"
    
    def test_prospect_to_dict(self, test_session_with_data):
        """Test converting prospect to dictionary."""
        prospect = test_session_with_data.query(Prospect).first()
        prospect_dict = ExportService._prospect_to_dict(prospect)
        
        assert prospect_dict["name"] == "Patrick Mahomes"
        assert prospect_dict["position"] == "QB"
        assert prospect_dict["height"] == 6.25
        assert prospect_dict["weight"] == 205
        assert isinstance(prospect_dict["id"], str)
        assert isinstance(prospect_dict["created_at"], str)
    
    def test_export_empty_result(self, test_session_with_data):
        """Test exporting with no matching records."""
        filters = QueryFilterSchema(position="K", skip=0, limit=100)
        
        json_str = ExportService.export_json(test_session_with_data, filters)
        data = json.loads(json_str)
        assert len(data) == 0
        assert data == []
    
    def test_export_with_limit(self, test_session_with_data):
        """Test export respects limit parameter."""
        filters = QueryFilterSchema(skip=0, limit=2)
        json_str = ExportService.export_json(test_session_with_data, filters)
        
        data = json.loads(json_str)
        assert len(data) == 2
    
    def test_export_with_skip(self, test_session_with_data):
        """Test export respects skip parameter."""
        filters = QueryFilterSchema(skip=1, limit=100)
        json_str = ExportService.export_json(test_session_with_data, filters)
        
        data = json.loads(json_str)
        assert len(data) == 2  # Skip 1, total 3
