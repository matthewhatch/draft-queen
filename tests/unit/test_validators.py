"""Unit tests for validation framework."""

import pytest
import os

# Set testing mode before importing app
os.environ["TESTING"] = "true"

from data_pipeline.models import ProspectDataSchema
from data_pipeline.validators import (
    SchemaValidator,
    BusinessRuleValidator,
    DuplicateDetector,
    ValidationResult,
)


class TestSchemaValidator:
    """Tests for schema validation."""
    
    def test_valid_prospect(self):
        """Test validation of valid prospect data."""
        data = {
            "name": "Patrick Mahomes",
            "position": "QB",
            "college": "Texas Tech",
            "height": 6.2,
            "weight": 220,
            "draft_grade": 8.7,
        }
        
        result = SchemaValidator.validate_prospect(data)
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_missing_required_field(self):
        """Test validation with missing required field."""
        data = {
            "position": "QB",
            "college": "Alabama",
            # Missing: name
        }
        
        result = SchemaValidator.validate_prospect(data)
        assert not result.is_valid
        assert len(result.errors) > 0
    
    def test_invalid_position(self):
        """Test validation with invalid position."""
        data = {
            "name": "Test Player",
            "position": "INVALID",
            "college": "Alabama",
        }
        
        result = SchemaValidator.validate_prospect(data)
        assert not result.is_valid
    
    def test_invalid_height_range(self):
        """Test validation with height out of range."""
        data = {
            "name": "Test Player",
            "position": "QB",
            "college": "Alabama",
            "height": 5.0,  # Below minimum
        }
        
        result = SchemaValidator.validate_prospect(data)
        assert not result.is_valid
    
    def test_batch_validation(self):
        """Test batch validation."""
        batch = [
            {
                "name": "Player 1",
                "position": "QB",
                "college": "Alabama",
            },
            {
                "name": "Player 2",
                "position": "RB",
                "college": "Georgia",
                "height": 5.83,  # 5'10" in decimal
                "weight": 205,
            },
            {
                # Invalid: missing position
                "name": "Player 3",
                "college": "Florida",
            },
        ]
        
        total, valid, invalid, errors = SchemaValidator.validate_batch(batch)
        assert total == 3
        assert valid == 2
        assert invalid == 1
        assert len(errors) == 1


class TestBusinessRuleValidator:
    """Tests for business rule validation."""
    
    def test_valid_height_range(self):
        """Test valid height."""
        is_valid, msg = BusinessRuleValidator.check_height_range(6.2)
        assert is_valid
        assert msg == ""
    
    def test_invalid_height_too_short(self):
        """Test height too short."""
        is_valid, msg = BusinessRuleValidator.check_height_range(5.0)
        assert not is_valid
        assert "outside realistic range" in msg
    
    def test_invalid_height_too_tall(self):
        """Test height too tall."""
        is_valid, msg = BusinessRuleValidator.check_height_range(7.5)
        assert not is_valid
        assert "outside realistic range" in msg
    
    def test_valid_weight_range(self):
        """Test valid weight."""
        is_valid, msg = BusinessRuleValidator.check_weight_range(220)
        assert is_valid
    
    def test_invalid_forty_time(self):
        """Test invalid 40-time."""
        is_valid, msg = BusinessRuleValidator.check_forty_time_range(6.0)
        assert not is_valid
    
    def test_measurable_consistency_high_bmi(self):
        """Test detection of high BMI."""
        warnings = BusinessRuleValidator.check_measurable_consistency(
            height=5.5,
            weight=350,
        )
        assert len(warnings) > 0
        assert "BMI" in warnings[0]


class TestDuplicateDetector:
    """Tests for duplicate detection."""
    
    def test_get_duplicate_key(self):
        """Test duplicate key generation."""
        prospect = {
            "name": "Patrick Mahomes",
            "position": "QB",
            "college": "Texas Tech",
        }
        
        key = DuplicateDetector.get_duplicate_key(prospect)
        assert key == ("patrick mahomes", "qb", "texas tech")
    
    def test_duplicate_key_case_insensitive(self):
        """Test that duplicate keys are case-insensitive."""
        p1 = {"name": "Patrick Mahomes", "position": "QB", "college": "Texas Tech"}
        p2 = {"name": "patrick mahomes", "position": "qb", "college": "texas tech"}
        
        key1 = DuplicateDetector.get_duplicate_key(p1)
        key2 = DuplicateDetector.get_duplicate_key(p2)
        
        assert key1 == key2
    
    def test_detect_duplicates_in_batch(self):
        """Test duplicate detection in batch."""
        batch = [
            {"name": "Player A", "position": "QB", "college": "Alabama"},
            {"name": "Player B", "position": "RB", "college": "Georgia"},
            {"name": "Player A", "position": "QB", "college": "Alabama"},  # Duplicate
            {"name": "Player C", "position": "WR", "college": "LSU"},
        ]
        
        duplicates = DuplicateDetector.detect_duplicates_in_batch(batch)
        
        assert len(duplicates) == 1
        key = ("player a", "qb", "alabama")
        assert key in duplicates
        assert duplicates[key] == [0, 2]  # Rows 0 and 2 are duplicates


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
