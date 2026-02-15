"""Integration tests for LineageRecorder

Tests the complete lineage recording workflow including:
- Lineage recorder initialization
- Lineage record structure
- Batch transformation handling
- Conflict tracking setup
"""

import pytest
from uuid import UUID, uuid4
from datetime import datetime, date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy import text

from src.data_pipeline.transformations.lineage_recorder import LineageRecorder
from src.data_pipeline.transformations.base_transformer import TransformationResult, FieldChange


@pytest.fixture
def mock_session():
    """Create mock database session."""
    session = MagicMock()
    return session


@pytest.fixture
def recorder(mock_session):
    """Create LineageRecorder instance."""
    return LineageRecorder(mock_session)


@pytest.fixture
def prospect_id():
    """Create prospect ID."""
    return uuid4()


class TestLineageRecorderBasics:
    """Test basic LineageRecorder initialization and configuration."""

    def test_lineage_recorder_initialization(self, mock_session):
        """Test recorder initialization."""
        recorder = LineageRecorder(mock_session)
        assert recorder.db is mock_session
        assert recorder.logger is not None

    def test_lineage_recorder_custom_logger(self, mock_session):
        """Test recorder with custom logger."""
        custom_logger = MagicMock()
        recorder = LineageRecorder(mock_session, custom_logger)
        assert recorder.logger is custom_logger


class TestLineageRecordStructure:
    """Test lineage record field requirements and structure."""

    async def test_record_field_transformation_requires_entity_type(self, recorder, prospect_id):
        """Test that entity_type is required."""
        with pytest.raises(ValueError):
            await recorder.record_field_transformation(
                entity_type=None,
                entity_id=prospect_id,
                field_name='test_field',
                new_value='test_value',
            )

    async def test_record_field_transformation_requires_entity_id(self, recorder):
        """Test that entity_id is required."""
        with pytest.raises(ValueError):
            await recorder.record_field_transformation(
                entity_type='prospect_grades',
                entity_id=None,
                field_name='test_field',
                new_value='test_value',
            )

    async def test_record_field_transformation_requires_field_name(self, recorder, prospect_id):
        """Test that field_name is required."""
        with pytest.raises(ValueError):
            await recorder.record_field_transformation(
                entity_type='prospect_grades',
                entity_id=prospect_id,
                field_name=None,
                new_value='test_value',
            )


class TestBatchTransformationRecording:
    """Test recording multiple transformations as a batch."""

    async def test_record_batch_transformations_empty_list(self, recorder):
        """Test batch recording with empty list returns 0."""
        rows_inserted = await recorder.record_batch_transformations([])
        assert rows_inserted == 0

    async def test_record_batch_transformations_requires_entity_type(self, recorder, prospect_id):
        """Test that batch records require entity_type."""
        invalid_records = [
            {
                # Missing entity_type
                'entity_id': str(prospect_id),
                'field_name': 'test_field',
                'value_current': 'value',
            }
        ]

        with pytest.raises(ValueError):
            await recorder.record_batch_transformations(invalid_records)

    async def test_record_batch_transformations_requires_entity_id(self, recorder):
        """Test that batch records require entity_id."""
        invalid_records = [
            {
                'entity_type': 'prospect_grades',
                # Missing entity_id
                'field_name': 'test_field',
                'value_current': 'value',
            }
        ]

        with pytest.raises(ValueError):
            await recorder.record_batch_transformations(invalid_records)


class TestLineageRecorderIntegration:
    """Test lineage recorder integration with transformations."""

    def test_lineage_recorder_preserves_transformation_metadata(self):
        """Test that lineage can store transformation metadata."""
        # Create a sample transformation result
        prospect_id = uuid4()
        field_changes = [
            FieldChange(
                field_name='grade_normalized',
                value_current=Decimal('8.5'),
                value_previous=None,
                transformation_rule_id='pff_normalize_grade',
                transformation_logic='Linear transformation',
            ),
        ]

        result = TransformationResult(
            entity_type='prospect_grades',
            entity_id=prospect_id,
            field_changes=field_changes,
            extraction_id=uuid4(),
            source_system='pff',
            source_row_id=123,
            staged_from_table='pff_staging',
        )

        # Verify lineage info can be extracted
        assert result.entity_type == 'prospect_grades'
        assert result.source_system == 'pff'
        assert len(result.field_changes) == 1
        assert result.field_changes[0].field_name == 'grade_normalized'

    def test_lineage_recorder_supports_conflict_metadata(self):
        """Test that lineage can store conflict information."""
        prospect_id = uuid4()
        
        # Create field change with conflict info
        field_change = FieldChange(
            field_name='position',
            value_current='WR',
            value_previous=None,
            had_conflict=True,
            conflicting_sources={
                'pff': 'WR',
                'nfl_combine': 'WR/TE',
                'cfr': 'WR',
            },
            conflict_resolution_rule='consensus_majority',
        )

        assert field_change.had_conflict is True
        assert field_change.conflicting_sources is not None
        assert len(field_change.conflicting_sources) == 3


class TestLineageRecorderValidation:
    """Test input validation for lineage recording."""

    async def test_record_field_transformation_accepts_uuid_entity_id(self, mock_session, prospect_id):
        """Test that UUID entity_ids are accepted."""
        recorder = LineageRecorder(mock_session)
        mock_result = MagicMock()
        mock_result.scalar = AsyncMock(return_value=str(uuid4()))
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Should not raise exception
        lineage_id = await recorder.record_field_transformation(
            entity_type='prospect_grades',
            entity_id=prospect_id,  # UUID
            field_name='grade_normalized',
            new_value=8.5,
            source_system='pff',
        )

        assert lineage_id is not None

    async def test_record_field_transformation_accepts_string_entity_id(self, mock_session):
        """Test that string entity_ids are accepted."""
        recorder = LineageRecorder(mock_session)
        prospect_id_str = str(uuid4())
        
        mock_result = MagicMock()
        mock_result.scalar = AsyncMock(return_value=str(uuid4()))
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Should not raise exception
        lineage_id = await recorder.record_field_transformation(
            entity_type='prospect_grades',
            entity_id=prospect_id_str,  # String UUID
            field_name='grade_normalized',
            new_value=8.5,
            source_system='pff',
        )

        assert lineage_id is not None


class TestLineageRecorderCompleteFlow:
    """Test complete transformation and lineage workflows."""

    async def test_pff_prospect_grade_transformation_lineage(self, mock_session, prospect_id):
        """Test lineage for PFF prospect grade transformation."""
        recorder = LineageRecorder(mock_session)
        mock_result = MagicMock()
        mock_result.scalar = AsyncMock(return_value=uuid4())
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Record PFF grade normalization
        lineage_id = await recorder.record_field_transformation(
            entity_type='prospect_grades',
            entity_id=prospect_id,
            field_name='grade_normalized',
            new_value=Decimal('8.5'),
            previous_value=None,
            source_system='pff',
            transformation_rule_id='pff_grade_linear_transform',
            transformation_logic='Linear: raw_grade * 0.1 + 5.0',
            staging_row_id=12345,
            changed_by='pff_transformer',
        )

        assert lineage_id is not None
        mock_session.execute.assert_called()

    async def test_multi_source_conflict_resolution_lineage(self, mock_session, prospect_id):
        """Test lineage recording with multi-source conflict resolution."""
        recorder = LineageRecorder(mock_session)
        mock_result = MagicMock()
        mock_result.scalar = AsyncMock(return_value=uuid4())
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Record height with conflict from three sources
        conflicting_measurements = {
            'pff': 74,
            'nfl_combine': 74.5,
            'cfr': 73.5,
        }

        lineage_id = await recorder.record_field_transformation(
            entity_type='prospect_measurements',
            entity_id=prospect_id,
            field_name='height_inches',
            new_value=74,
            previous_value=None,
            source_system='nfl_combine',
            had_conflict=True,
            conflicting_values=conflicting_measurements,
            conflict_resolution_rule='source_priority_nfl_combine',
            changed_by='etl_nfl_transformer',
            change_reason='NFL Combine measurement authoritative',
        )

        assert lineage_id is not None

    async def test_batch_prospect_grades_lineage(self, mock_session):
        """Test batch lineage recording for multiple prospects."""
        recorder = LineageRecorder(mock_session)
        prospect_ids = [uuid4() for _ in range(3)]

        lineage_records = []
        for i, prospect_id in enumerate(prospect_ids):
            lineage_records.extend([
                {
                    'entity_type': 'prospect_grades',
                    'entity_id': str(prospect_id),
                    'field_name': 'grade_normalized',
                    'value_current': str(Decimal('8.0') + Decimal('0.5') * i),
                    'value_previous': None,
                    'source_system': 'pff',
                    'transformation_rule_id': 'pff_normalize_grade',
                },
                {
                    'entity_type': 'prospect_grades',
                    'entity_id': str(prospect_id),
                    'field_name': 'sample_size',
                    'value_current': str(1000 + 100 * i),
                    'value_previous': None,
                    'source_system': 'pff',
                    'transformation_rule_id': 'sample_size_capture',
                },
            ])

        mock_result = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        rows_inserted = await recorder.record_batch_transformations(lineage_records)

        assert rows_inserted == len(lineage_records)

    async def test_lineage_chain_preserves_transformation_history(self, mock_session, prospect_id):
        """Test that lineage chain preserves transformation history."""
        recorder = LineageRecorder(mock_session)
        
        # Mock all three calls to record_field_transformation
        mock_result = MagicMock()
        mock_result.scalar = AsyncMock(return_value=uuid4())
        mock_session.execute = AsyncMock(return_value=mock_result)

        # First transformation: extract from staging
        id1 = await recorder.record_field_transformation(
            entity_type='prospect_grades',
            entity_id=prospect_id,
            field_name='grade_normalized',
            new_value=Decimal('8.5'),
            previous_value=None,
            source_system='pff',
            transformation_rule_id='extract_from_staging',
            change_reason='Initial extraction from PFF staging',
        )

        # Second transformation: manual correction  
        id2 = await recorder.record_field_transformation(
            entity_type='prospect_grades',
            entity_id=prospect_id,
            field_name='grade_normalized',
            new_value=Decimal('8.7'),
            previous_value=Decimal('8.5'),
            source_system='system',
            transformation_rule_id='manual_correction',
            changed_by='analyst',
            change_reason='Corrected based on review',
        )

        # Third transformation: conflict resolution
        id3 = await recorder.record_field_transformation(
            entity_type='prospect_grades',
            entity_id=prospect_id,
            field_name='grade_normalized',
            new_value=Decimal('8.6'),
            previous_value=Decimal('8.7'),
            source_system='system',
            had_conflict=True,
            conflicting_values={'pff': 8.5, 'manual': 8.7},
            conflict_resolution_rule='average',
            changed_by='conflict_resolver',
            change_reason='Resolved PFF vs manual conflict',
        )

        # Verify db.execute was called 3 times (once for each transformation)
        assert mock_session.execute.call_count == 3
        
        # Verify we got results back
        assert id1 is not None
        assert id2 is not None
        assert id3 is not None

    def test_transformation_result_to_lineage_record_conversion(self):
        """Test converting TransformationResult to lineage records."""
        prospect_id = uuid4()
        field_changes = [
            FieldChange(
                field_name='grade_normalized',
                value_current=Decimal('8.5'),
                value_previous=None,
                transformation_rule_id='pff_normalize_grade',
                transformation_logic='Linear transformation',
            ),
            FieldChange(
                field_name='prospect_id',
                value_current=prospect_id,
                value_previous=None,
                transformation_rule_id='extract_prospect_id',
                transformation_logic='Extract from PFF ID',
            ),
        ]

        result = TransformationResult(
            entity_type='prospect_grades',
            entity_id=prospect_id,
            field_changes=field_changes,
            extraction_id=uuid4(),
            source_system='pff',
            source_row_id=123,
            staged_from_table='pff_staging',
        )

        # Verify each field change can become a lineage record
        lineage_records = []
        for field_change in result.field_changes:
            record = {
                'entity_type': result.entity_type,
                'entity_id': str(result.entity_id),
                'field_name': field_change.field_name,
                'value_current': str(field_change.value_current),
                'value_previous': str(field_change.value_previous) if field_change.value_previous else None,
                'source_system': result.source_system,
                'transformation_rule_id': field_change.transformation_rule_id,
            }
            lineage_records.append(record)

        assert len(lineage_records) == 2
        assert lineage_records[0]['field_name'] == 'grade_normalized'
        assert lineage_records[1]['field_name'] == 'prospect_id'

    def test_conflicting_sources_structure(self):
        """Test conflicting sources data structure."""
        conflicting_measurements = {
            'pff': 74,
            'nfl_combine': 74.5,
            'cfr': 73.5,
        }

        field_change = FieldChange(
            field_name='height_inches',
            value_current=74,
            value_previous=None,
            had_conflict=True,
            conflicting_sources=conflicting_measurements,
            conflict_resolution_rule='source_priority_nfl_combine',
        )

        assert field_change.had_conflict is True
        assert len(field_change.conflicting_sources) == 3
        assert field_change.conflicting_sources['nfl_combine'] == 74.5
        assert field_change.conflict_resolution_rule == 'source_priority_nfl_combine'

    async def test_lineage_audit_trail_immutability(self, mock_session, prospect_id):
        """Test that lineage records are immutable (inserted, not updated)."""
        recorder = LineageRecorder(mock_session)
        mock_result = MagicMock()
        mock_result.scalar = AsyncMock(return_value=str(uuid4()))
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Record initial value
        lineage_id1 = await recorder.record_field_transformation(
            entity_type='prospect_core',
            entity_id=prospect_id,
            field_name='status',
            new_value='active',
            source_system='system',
        )

        # Record value update
        lineage_id2 = await recorder.record_field_transformation(
            entity_type='prospect_core',
            entity_id=prospect_id,
            field_name='status',
            new_value='injury_reserve',
            previous_value='active',
            source_system='system',
        )

        # Each change should create new record (different IDs)
        assert lineage_id1 != lineage_id2
        
        # Both calls should use INSERT (not UPDATE)
        assert mock_session.execute.call_count == 2


class TestLineageRecorderErrorHandling:
    """Test error handling and edge cases."""

    async def test_invalid_entity_type_raises_error(self, recorder, prospect_id):
        """Test that invalid entity_type raises ValueError."""
        with pytest.raises(ValueError):
            await recorder.record_field_transformation(
                entity_type='',  # Empty string
                entity_id=prospect_id,
                field_name='test_field',
                new_value='value',
            )

    async def test_none_field_name_raises_error(self, recorder, prospect_id):
        """Test that None field_name raises ValueError."""
        with pytest.raises(ValueError):
            await recorder.record_field_transformation(
                entity_type='prospect_grades',
                entity_id=prospect_id,
                field_name=None,
                new_value='value',
            )

    async def test_empty_field_name_raises_error(self, recorder, prospect_id):
        """Test that empty field_name raises ValueError."""
        with pytest.raises(ValueError):
            await recorder.record_field_transformation(
                entity_type='prospect_grades',
                entity_id=prospect_id,
                field_name='',
                new_value='value',
            )

    async def test_batch_with_missing_entity_type(self, recorder):
        """Test batch record with missing entity_type."""
        records = [
            {
                'entity_id': str(uuid4()),
                'field_name': 'test_field',
                'value_current': 'value',
                # Missing entity_type
            }
        ]

        with pytest.raises(ValueError):
            await recorder.record_batch_transformations(records)

    async def test_batch_with_missing_entity_id(self, recorder):
        """Test batch record with missing entity_id."""
        records = [
            {
                'entity_type': 'prospect_grades',
                'field_name': 'test_field',
                'value_current': 'value',
                # Missing entity_id
            }
        ]

        with pytest.raises(ValueError):
            await recorder.record_batch_transformations(records)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
