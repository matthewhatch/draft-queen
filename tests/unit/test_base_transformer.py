"""Unit tests for base transformer framework

Tests cover:
- TransformationResult and FieldChange dataclasses
- BaseTransformer abstract base class
- Validation utilities
- Field change tracking
- Lineage recording utilities
"""

import pytest
from uuid import uuid4
from datetime import datetime
from typing import Dict, Any, Optional

from data_pipeline.transformations.base_transformer import (
    BaseTransformer,
    TransformationResult,
    FieldChange,
    TransformationPhase,
    ValidationError,
)
from data_pipeline.transformations.lineage_recorder import LineageRecorder


# ========== FIXTURES ==========

@pytest.fixture
def extraction_id():
    return uuid4()


@pytest.fixture
def prospect_id():
    return uuid4()


@pytest.fixture
def mock_db_session():
    """Mock database session for testing"""
    class MockDB:
        async def execute(self, query, params=None):
            # Mock response
            class Result:
                def scalar(self):
                    return uuid4()
                def fetchall(self):
                    return []
            return Result()
    
    return MockDB()


# ========== TEST FIELDCHANGE DATACLASS ==========

class TestFieldChange:
    """Tests for FieldChange dataclass"""
    
    def test_field_change_basic(self):
        """Test basic FieldChange creation"""
        change = FieldChange(
            field_name='grade_normalized',
            value_current=9.375,
            value_previous=None,
        )
        
        assert change.field_name == 'grade_normalized'
        assert change.value_current == 9.375
        assert change.value_previous is None
        assert change.had_conflict is False
    
    def test_field_change_with_conflict(self):
        """Test FieldChange with conflict resolution"""
        change = FieldChange(
            field_name='height_inches',
            value_current=74,
            value_previous=73,
            had_conflict=True,
            conflicting_sources={'nfl_combine': 74, 'pff': 73},
            conflict_resolution_rule='most_recent',
        )
        
        assert change.had_conflict is True
        assert change.conflicting_sources['nfl_combine'] == 74
        assert change.conflict_resolution_rule == 'most_recent'


# ========== TEST TRANSFORMATIONRESULT DATACLASS ==========

class TestTransformationResult:
    """Tests for TransformationResult dataclass"""
    
    def test_transformation_result_basic(self, prospect_id, extraction_id):
        """Test basic TransformationResult creation"""
        change = FieldChange(
            field_name='grade_normalized',
            value_current=9.375,
            transformation_rule_id='pff_grade_normalize',
        )
        
        result = TransformationResult(
            entity_id=prospect_id,
            entity_type='prospect_grades',
            field_changes=[change],
            extraction_id=extraction_id,
            source_system='pff',
            source_row_id=123,
            staged_from_table='pff_staging',
        )
        
        assert result.entity_id == prospect_id
        assert result.entity_type == 'prospect_grades'
        assert len(result.field_changes) == 1
        assert result.source_system == 'pff'
    
    def test_get_lineage_records(self, prospect_id, extraction_id):
        """Test converting transformation result to lineage records"""
        changes = [
            FieldChange(
                field_name='grade_raw',
                value_current=87.5,
                transformation_rule_id='pff_extract',
                transformation_logic='direct from PFF',
            ),
            FieldChange(
                field_name='grade_normalized',
                value_current=9.375,
                value_previous=None,
                transformation_rule_id='pff_grade_normalize',
                transformation_logic='grade = 5.0 + (raw / 100 * 5.0)',
            ),
        ]
        
        result = TransformationResult(
            entity_id=prospect_id,
            entity_type='prospect_grades',
            field_changes=changes,
            extraction_id=extraction_id,
            source_system='pff',
            source_row_id=123,
            staged_from_table='pff_staging',
        )
        
        lineage_records = result.get_lineage_records()
        
        assert len(lineage_records) == 2
        assert lineage_records[0]['field_name'] == 'grade_raw'
        assert lineage_records[0]['source_system'] == 'pff'
        assert lineage_records[0]['changed_at'] is not None
        assert lineage_records[1]['field_name'] == 'grade_normalized'


# ========== TEST BASE TRANSFORMER ==========

class ConcreteTransformer(BaseTransformer):
    """Concrete implementation of BaseTransformer for testing"""
    
    SOURCE_NAME = 'test_source'
    STAGING_TABLE_NAME = 'test_staging'
    
    async def validate_staging_data(self, row: Dict) -> bool:
        """Simple validation: require id and name"""
        return bool(row.get('id') and row.get('name'))
    
    async def get_prospect_identity(self, row: Dict) -> Optional[Dict]:
        """Extract identity from row"""
        if not row.get('name'):
            return None
        
        return {
            'name_first': row.get('name').split()[0],
            'name_last': row.get('name').split()[-1] if len(row.get('name').split()) > 1 else '',
            'position': row.get('position'),
            'college': row.get('college'),
        }
    
    async def transform_staging_to_canonical(
        self, row: Dict, prospect_id
    ) -> TransformationResult:
        """Simple transformation"""
        return TransformationResult(
            entity_id=prospect_id,
            entity_type='prospect_core',
            field_changes=[
                FieldChange(
                    field_name='name_first',
                    value_current=row.get('name').split()[0],
                )
            ],
            extraction_id=self.extraction_id,
            source_system=self.source_name,
            source_row_id=row.get('id'),
            staged_from_table=self.staging_table,
        )
    
    async def _match_or_create_prospect(self, identity: Dict, row: Dict):
        """Mock: always return same ID"""
        return uuid4()


class TestBaseTransformer:
    """Tests for BaseTransformer base class"""
    
    def test_transformer_initialization(self, mock_db_session, extraction_id):
        """Test transformer initialization"""
        transformer = ConcreteTransformer(mock_db_session, extraction_id)
        
        assert transformer.source_name == 'test_source'
        assert transformer.staging_table == 'test_staging'
        assert transformer.extraction_id == extraction_id
        assert transformer.stats['validated'] == 0
    
    def test_transformer_missing_source_name(self, mock_db_session, extraction_id):
        """Test that transformer raises if SOURCE_NAME not set"""
        class BadTransformer(BaseTransformer):
            STAGING_TABLE_NAME = 'test'
            async def validate_staging_data(self, row): pass
            async def get_prospect_identity(self, row): pass
            async def transform_staging_to_canonical(self, row, id): pass
            async def _match_or_create_prospect(self, id, row): pass
        
        with pytest.raises(ValueError, match="SOURCE_NAME"):
            BadTransformer(mock_db_session, extraction_id)
    
    @pytest.mark.asyncio
    async def test_process_staging_batch(self, mock_db_session, extraction_id):
        """Test batch processing"""
        transformer = ConcreteTransformer(mock_db_session, extraction_id)
        
        staging_rows = [
            {'id': 1, 'name': 'John Doe', 'position': 'QB', 'college': 'Alabama'},
            {'id': 2, 'name': 'Jane Smith', 'position': 'WR', 'college': 'Ohio State'},
        ]
        
        successes, failures = await transformer.process_staging_batch(staging_rows)
        
        assert len(successes) == 2
        assert len(failures) == 0
        assert transformer.stats['validated'] == 2
        assert transformer.stats['matched'] == 2
    
    @pytest.mark.asyncio
    async def test_process_staging_batch_with_failures(self, mock_db_session, extraction_id):
        """Test batch processing with validation failures"""
        transformer = ConcreteTransformer(mock_db_session, extraction_id)
        
        staging_rows = [
            {'id': 1, 'name': 'John Doe', 'position': 'QB', 'college': 'Alabama'},
            {'id': 2},  # Missing 'name' - will fail validation
            {'name': 'Jane Smith', 'position': 'WR', 'college': 'Ohio State'},  # Missing 'id'
        ]
        
        successes, failures = await transformer.process_staging_batch(staging_rows)
        
        assert len(successes) == 1
        assert len(failures) == 2
        assert failures[0]['reason'] == 'validation_failed'
    
    def test_validate_field_type_check(self, mock_db_session, extraction_id):
        """Test field validation with type checking"""
        transformer = ConcreteTransformer(mock_db_session, extraction_id)
        
        is_valid, error = transformer.validate_field('grade', 87.5, float)
        assert is_valid is True
        assert error is None
        
        is_valid, error = transformer.validate_field('grade', 'invalid', float)
        assert is_valid is False
        assert 'must be float' in error
    
    def test_validate_field_range(self, mock_db_session, extraction_id):
        """Test field validation with min/max"""
        transformer = ConcreteTransformer(mock_db_session, extraction_id)
        
        is_valid, error = transformer.validate_field('grade', 50, int, min_value=0, max_value=100)
        assert is_valid is True
        
        is_valid, error = transformer.validate_field('grade', 150, int, min_value=0, max_value=100)
        assert is_valid is False
        assert 'must be <=' in error
    
    def test_validate_field_allowed_values(self, mock_db_session, extraction_id):
        """Test field validation with allowed values"""
        transformer = ConcreteTransformer(mock_db_session, extraction_id)
        
        positions = ['QB', 'RB', 'WR', 'TE']
        
        is_valid, error = transformer.validate_field('position', 'QB', str, allowed_values=positions)
        assert is_valid is True
        
        is_valid, error = transformer.validate_field('position', 'K', str, allowed_values=positions)
        assert is_valid is False
        assert 'must be one of' in error
    
    def test_create_field_change(self, mock_db_session, extraction_id):
        """Test creating field change record"""
        transformer = ConcreteTransformer(mock_db_session, extraction_id)
        
        change = transformer.create_field_change(
            field_name='grade_normalized',
            new_value=9.375,
            old_value=None,
            transformation_rule_id='pff_normalize',
            transformation_logic='linear scaling',
        )
        
        assert change.field_name == 'grade_normalized'
        assert change.value_current == 9.375
        assert change.transformation_rule_id == 'pff_normalize'
    
    def test_record_conflict(self, mock_db_session, extraction_id):
        """Test recording conflicting values"""
        transformer = ConcreteTransformer(mock_db_session, extraction_id)
        
        change = transformer.record_conflict(
            field_name='height_inches',
            resolved_value=74,
            conflicting_sources={'nfl_combine': 74, 'pff': 73},
            resolution_rule='most_recent',
        )
        
        assert change.had_conflict is True
        assert change.value_current == 74
        assert change.conflicting_sources['pff'] == 73
        assert change.conflict_resolution_rule == 'most_recent'
    
    def test_get_stats(self, mock_db_session, extraction_id):
        """Test retrieving statistics"""
        transformer = ConcreteTransformer(mock_db_session, extraction_id)
        transformer.stats['validated'] = 100
        transformer.stats['matched'] = 95
        
        stats = transformer.get_stats()
        
        assert stats['validated'] == 100
        assert stats['matched'] == 95
        # Verify it's a copy (modifying returned stats doesn't affect internal)
        stats['validated'] = 999
        assert transformer.stats['validated'] == 100


# ========== TEST LINEAGE RECORDER ==========

class TestLineageRecorder:
    """Tests for LineageRecorder"""
    
    def test_lineage_recorder_initialization(self, mock_db_session):
        """Test lineage recorder initialization"""
        recorder = LineageRecorder(mock_db_session)
        assert recorder.db is mock_db_session
    
    @pytest.mark.asyncio
    async def test_record_field_transformation(self, mock_db_session, prospect_id):
        """Test recording a single field transformation"""
        recorder = LineageRecorder(mock_db_session)
        
        lineage_id = await recorder.record_field_transformation(
            entity_type='prospect_grades',
            entity_id=prospect_id,
            field_name='grade_normalized',
            new_value=9.375,
            previous_value=None,
            staging_row_id=123,
            source_system='pff',
            transformation_rule_id='pff_grade_normalize',
            transformation_logic='grade = 5.0 + (raw / 100 * 5.0)',
        )
        
        assert lineage_id is not None
    
    @pytest.mark.asyncio
    async def test_record_field_transformation_with_conflict(self, mock_db_session, prospect_id):
        """Test recording transformation with conflicting sources"""
        recorder = LineageRecorder(mock_db_session)
        
        lineage_id = await recorder.record_field_transformation(
            entity_type='prospect_measurements',
            entity_id=prospect_id,
            field_name='height_inches',
            new_value=74,
            previous_value=73,
            staging_row_id=456,
            source_system='nfl_combine',
            transformation_rule_id='height_resolve_conflict',
            had_conflict=True,
            conflicting_values={'nfl_combine': 74, 'pff': 73},
            conflict_resolution_rule='most_recent',
        )
        
        assert lineage_id is not None
    
    @pytest.mark.asyncio
    async def test_record_field_transformation_missing_required_fields(self, mock_db_session):
        """Test that required fields are validated"""
        recorder = LineageRecorder(mock_db_session)
        
        with pytest.raises(ValueError, match="Required parameters"):
            await recorder.record_field_transformation(
                entity_type='prospect_grades',
                entity_id=None,  # Missing required field
                field_name='grade_normalized',
                new_value=9.375,
            )
    
    @pytest.mark.asyncio
    async def test_record_batch_transformations(self, mock_db_session, prospect_id, extraction_id):
        """Test recording multiple transformations in batch"""
        recorder = LineageRecorder(mock_db_session)
        
        records = [
            {
                'entity_type': 'prospect_grades',
                'entity_id': prospect_id,
                'field_name': 'grade_raw',
                'value_current': 87.5,
                'source_system': 'pff',
                'transformation_rule_id': 'pff_extract',
            },
            {
                'entity_type': 'prospect_grades',
                'entity_id': prospect_id,
                'field_name': 'grade_normalized',
                'value_current': 9.375,
                'source_system': 'pff',
                'transformation_rule_id': 'pff_normalize',
            },
        ]
        
        count = await recorder.record_batch_transformations(records)
        assert count == 2


# ========== TEST TRANSFORMATION PHASES ==========

class TestTransformationPhase:
    """Tests for TransformationPhase enum"""
    
    def test_phase_values(self):
        """Test phase enum values"""
        assert TransformationPhase.VALIDATE.value == "validate"
        assert TransformationPhase.MATCH.value == "match"
        assert TransformationPhase.NORMALIZE.value == "normalize"
        assert TransformationPhase.RECONCILE.value == "reconcile"
        assert TransformationPhase.LOAD.value == "load"


# ========== INTEGRATION TESTS ==========

class TestTransformerIntegration:
    """Integration tests for complete transformation flow"""
    
    @pytest.mark.asyncio
    async def test_complete_transformation_flow(self, mock_db_session, extraction_id, prospect_id):
        """Test complete transformation pipeline"""
        transformer = ConcreteTransformer(mock_db_session, extraction_id)
        
        # Simulate complete flow
        staging_row = {
            'id': 1,
            'name': 'John Doe',
            'position': 'QB',
            'college': 'Alabama',
        }
        
        # Validate
        is_valid = await transformer.validate_staging_data(staging_row)
        assert is_valid is True
        
        # Extract identity
        identity = await transformer.get_prospect_identity(staging_row)
        assert identity['name_first'] == 'John'
        
        # Match/create prospect
        matched_id = await transformer._match_or_create_prospect(identity, staging_row)
        assert matched_id is not None
        
        # Transform
        result = await transformer.transform_staging_to_canonical(staging_row, matched_id)
        assert result.entity_type == 'prospect_core'
        assert len(result.field_changes) > 0
        
        # Get lineage records
        lineage_records = result.get_lineage_records()
        assert len(lineage_records) > 0
        assert lineage_records[0]['entity_id'] == matched_id if isinstance(matched_id, str) else str(matched_id)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
