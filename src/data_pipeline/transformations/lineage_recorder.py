"""Lineage Recording Utility

This module provides utilities for recording complete data lineage - the audit trail
showing where every field value came from, how it was transformed, and when it changed.

Classes:
- LineageRecorder: Records transformations to data_lineage table
"""

from uuid import UUID
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class LineageRecorder:
    """
    Records complete audit trail of data transformations.
    
    Usage:
        recorder = LineageRecorder(db_session)
        await recorder.record_field_transformation(
            entity_type='prospect_grades',
            entity_id=prospect_id,
            field_name='grade_normalized',
            new_value=9.375,
            previous_value=None,
            staging_row_id=123,
            source_system='pff',
            transformation_rule_id='pff_grade_normalization',
            transformation_logic="grade = 5.0 + (raw / 100 * 5.0)",
        )
    """
    
    def __init__(self, db_session, logger_instance=None):
        """
        Initialize lineage recorder.
        
        Args:
            db_session: Database session for inserting lineage records
            logger_instance: Optional logger instance
        """
        self.db = db_session
        self.logger = logger_instance or logging.getLogger(self.__class__.__name__)
    
    async def record_field_transformation(
        self,
        entity_type: str,
        entity_id: UUID,
        field_name: str,
        new_value: Any,
        previous_value: Optional[Any] = None,
        staging_row_id: Optional[int] = None,
        source_system: Optional[str] = None,
        transformation_rule_id: str = "",
        transformation_logic: str = "",
        had_conflict: bool = False,
        conflicting_values: Optional[Dict] = None,
        conflict_resolution_rule: Optional[str] = None,
        changed_by: str = 'system',
        change_reason: Optional[str] = None,
    ) -> UUID:
        """
        Record single field transformation to data_lineage table.
        
        This creates an immutable record of:
        - What changed (field_name)
        - What the value was before/after (previous/new)
        - Where it came from (source_system, staging_row_id)
        - How it was transformed (transformation_rule_id, transformation_logic)
        - When it changed (changed_at, automatic timestamp)
        - Whether there were conflicts (conflicting_values, resolution_rule)
        
        Args:
            entity_type: Type of entity (prospect_core, prospect_grades, etc.)
            entity_id: ID of entity being changed
            field_name: Name of field that changed
            new_value: New value
            previous_value: Old value (optional, None for inserts)
            staging_row_id: ID of row in staging table
            source_system: Which external source (pff, nfl_combine, cfr, etc.)
            transformation_rule_id: ID of transformation rule applied
            transformation_logic: Human-readable description of transformation
            had_conflict: Whether multiple sources provided different values
            conflicting_values: {source_name: value, ...} for conflicts
            conflict_resolution_rule: How conflict was resolved
            changed_by: Who/what made the change (default: system)
            change_reason: Why was it changed? (optional, for manual overrides)
            
        Returns:
            UUID of created lineage record
            
        Raises:
            ValueError: If required parameters are missing
        """
        if not entity_type or not entity_id or not field_name:
            raise ValueError(
                f"Required parameters missing: entity_type={entity_type}, "
                f"entity_id={entity_id}, field_name={field_name}"
            )
        
        # Create lineage record
        lineage_record = {
            'entity_type': entity_type,
            'entity_id': str(entity_id),
            'field_name': field_name,
            'value_current': str(new_value) if new_value is not None else None,
            'value_previous': str(previous_value) if previous_value is not None else None,
            'value_is_null': new_value is None,
            'extraction_id': None,  # Will be set by caller if needed
            'source_table': f'{source_system}_staging' if source_system else None,
            'source_row_id': staging_row_id,
            'source_system': source_system,
            'transformation_rule_id': transformation_rule_id,
            'transformation_logic': transformation_logic,
            'transformation_is_automated': changed_by == 'system',
            'had_conflict': had_conflict,
            'conflicting_sources': conflicting_values,
            'conflict_resolution_rule': conflict_resolution_rule,
            'changed_at': datetime.utcnow(),
            'changed_by': changed_by,
            'change_reason': change_reason,
        }
        
        # Insert into data_lineage table
        try:
            # Raw SQL insert (faster than ORM for bulk inserts)
            from sqlalchemy import text
            
            result = await self.db.execute(text("""
                INSERT INTO data_lineage
                (entity_type, entity_id, field_name, value_current, value_previous,
                 value_is_null, source_table, source_row_id, source_system,
                 transformation_rule_id, transformation_logic, transformation_is_automated,
                 had_conflict, conflicting_sources, conflict_resolution_rule,
                 changed_at, changed_by, change_reason)
                VALUES
                (:entity_type, :entity_id, :field_name, :value_current, :value_previous,
                 :value_is_null, :source_table, :source_row_id, :source_system,
                 :transformation_rule_id, :transformation_logic, :transformation_is_automated,
                 :had_conflict, :conflicting_sources, :conflict_resolution_rule,
                 :changed_at, :changed_by, :change_reason)
                RETURNING id
            """), lineage_record)
            
            lineage_id = result.scalar()
            
            self.logger.debug(
                f"Lineage recorded: {entity_type}:{entity_id}.{field_name} "
                f"from {source_system} (rule: {transformation_rule_id})"
            )
            
            return lineage_id
            
        except Exception as e:
            self.logger.error(
                f"Failed to record lineage for {entity_type}:{entity_id}.{field_name}: {e}",
                exc_info=True
            )
            raise
    
    async def record_batch_transformations(
        self,
        lineage_records: List[Dict],
    ) -> int:
        """
        Record multiple field transformations in batch (faster).
        
        Args:
            lineage_records: List of dicts with transformation info
            
        Returns:
            Number of records inserted
            
        Raises:
            ValueError: If records are malformed
        """
        if not lineage_records:
            return 0
        
        from sqlalchemy import text
        
        # Prepare records for batch insert
        for record in lineage_records:
            if not record.get('entity_type') or not record.get('entity_id'):
                raise ValueError(f"Malformed lineage record: {record}")
            
            # Convert UUIDs to strings
            if isinstance(record.get('entity_id'), UUID):
                record['entity_id'] = str(record['entity_id'])
            if isinstance(record.get('extraction_id'), UUID):
                record['extraction_id'] = str(record['extraction_id'])
            
            # Set timestamp if not provided
            if not record.get('changed_at'):
                record['changed_at'] = datetime.utcnow()
            
            # Default changed_by to system
            if not record.get('changed_by'):
                record['changed_by'] = 'system'
        
        try:
            count = 0
            for record in lineage_records:
                await self.db.execute(text("""
                    INSERT INTO data_lineage
                    (entity_type, entity_id, field_name, value_current, value_previous,
                     value_is_null, extraction_id, source_table, source_row_id, source_system,
                     transformation_rule_id, transformation_logic, transformation_is_automated,
                     had_conflict, conflicting_sources, conflict_resolution_rule,
                     changed_at, changed_by, change_reason)
                    VALUES
                    (:entity_type, :entity_id, :field_name, :value_current, :value_previous,
                     :value_is_null, :extraction_id, :source_table, :source_row_id, :source_system,
                     :transformation_rule_id, :transformation_logic, :transformation_is_automated,
                     :had_conflict, :conflicting_sources, :conflict_resolution_rule,
                     :changed_at, :changed_by, :change_reason)
                """), record)
                count += 1
            
            self.logger.info(f"Recorded {count} lineage entries")
            return count
            
        except Exception as e:
            self.logger.error(f"Failed to record batch lineage: {e}", exc_info=True)
            raise
    
    async def get_lineage_for_entity(
        self,
        entity_type: str,
        entity_id: UUID,
        field_name: Optional[str] = None,
    ) -> List[Dict]:
        """
        Query complete lineage for an entity or specific field.
        
        Args:
            entity_type: Type of entity (prospect_core, prospect_grades, etc.)
            entity_id: ID of entity
            field_name: Optional specific field to query
            
        Returns:
            List of lineage records in chronological order
            
        Example:
            lineage = await recorder.get_lineage_for_entity(
                'prospect_grades', prospect_id, 'grade_normalized'
            )
            for record in lineage:
                print(f"{record['changed_at']}: {record['value_previous']} → {record['value_current']}")
        """
        from sqlalchemy import text
        
        if field_name:
            result = await self.db.execute(text("""
                SELECT * FROM data_lineage
                WHERE entity_type = :entity_type
                  AND entity_id = :entity_id
                  AND field_name = :field_name
                ORDER BY changed_at ASC
            """), {
                'entity_type': entity_type,
                'entity_id': str(entity_id),
                'field_name': field_name,
            })
        else:
            result = await self.db.execute(text("""
                SELECT * FROM data_lineage
                WHERE entity_type = :entity_type
                  AND entity_id = :entity_id
                ORDER BY changed_at ASC, field_name ASC
            """), {
                'entity_type': entity_type,
                'entity_id': str(entity_id),
            })
        
        rows = result.fetchall()
        return [dict(row) for row in rows] if rows else []
    
    async def get_conflicts_for_field(
        self,
        entity_type: str,
        field_name: str,
    ) -> List[Dict]:
        """
        Find all instances where this field had conflicting values.
        
        Args:
            entity_type: Type of entity
            field_name: Field name
            
        Returns:
            List of records where had_conflict=True
        """
        from sqlalchemy import text
        
        result = await self.db.execute(text("""
            SELECT * FROM data_lineage
            WHERE entity_type = :entity_type
              AND field_name = :field_name
              AND had_conflict = true
            ORDER BY changed_at DESC
        """), {
            'entity_type': entity_type,
            'field_name': field_name,
        })
        
        rows = result.fetchall()
        return [dict(row) for row in rows] if rows else []
