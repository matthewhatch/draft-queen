"""Base transformer framework for ETL pipeline

This module provides abstract base classes and utilities for all source-specific
transformers. Transformers convert raw staging data to canonical business entities.

Classes:
- BaseTransformer: Abstract base for all transformers
- TransformationResult: Result object for a transformation
- ValidationError: Custom exception for validation failures
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Tuple
from uuid import UUID
from datetime import datetime
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class TransformationPhase(str, Enum):
    """ETL transformation phases"""
    VALIDATE = "validate"
    MATCH = "match"
    NORMALIZE = "normalize"
    RECONCILE = "reconcile"
    LOAD = "load"


class ValidationError(Exception):
    """Raised when staging data validation fails"""
    pass


@dataclass
class FieldChange:
    """Record of a single field change"""
    field_name: str
    value_current: Any
    value_previous: Optional[Any] = None
    transformation_rule_id: str = ""
    transformation_logic: str = ""
    had_conflict: bool = False
    conflicting_sources: Optional[Dict] = None
    conflict_resolution_rule: Optional[str] = None


@dataclass
class TransformationResult:
    """Result of transforming staging data to canonical form"""
    entity_id: UUID
    entity_type: str  # prospect_core, prospect_grades, etc.
    field_changes: List[FieldChange]  # All field transformations
    extraction_id: UUID  # Which ETL run
    source_system: str  # pff, nfl_combine, cfr, etc.
    source_row_id: int  # ID in staging table
    staged_from_table: str  # e.g., pff_staging
    
    # Optional: for new entity creation
    new_entity_created: bool = False
    entity_created_from: str = ""  # If new, which source created it
    
    # Metadata
    had_conflicts: bool = False
    warnings: List[str] = field(default_factory=list)
    
    def get_lineage_records(self) -> List[Dict]:
        """Convert field changes to lineage table records"""
        records = []
        for change in self.field_changes:
            records.append({
                'entity_type': self.entity_type,
                'entity_id': self.entity_id,
                'field_name': change.field_name,
                'value_current': str(change.value_current) if change.value_current is not None else None,
                'value_previous': str(change.value_previous) if change.value_previous is not None else None,
                'extraction_id': self.extraction_id,
                'source_table': self.staged_from_table,
                'source_row_id': self.source_row_id,
                'source_system': self.source_system,
                'transformation_rule_id': change.transformation_rule_id,
                'transformation_logic': change.transformation_logic,
                'had_conflict': change.had_conflict,
                'conflicting_sources': change.conflicting_sources,
                'conflict_resolution_rule': change.conflict_resolution_rule,
                'changed_at': datetime.utcnow(),
                'changed_by': 'system',
            })
        return records


class BaseTransformer(ABC):
    """
    Abstract base class for all ETL transformers.
    
    Transformers are responsible for:
    1. Validating raw staging data
    2. Extracting prospect identity from staging
    3. Matching prospects across sources
    4. Normalizing values to canonical form
    5. Recording lineage for audit trail
    6. Detecting and resolving conflicts
    
    Each source (PFF, NFL, CFR, etc.) should implement a subclass.
    
    Usage:
        class PFFTransformer(BaseTransformer):
            def validate_staging_data(self, row: Dict) -> bool: ...
            def get_prospect_identity(self, row: Dict) -> Optional[Dict]: ...
            def transform_staging_to_canonical(self, row: Dict, prospect_id: UUID): ...
        
        transformer = PFFTransformer(db_session, pipeline_run_id)
        results, failures = await transformer.process_staging_batch(staging_rows)
    """
    
    # Subclasses should override these
    SOURCE_NAME: str = None  # e.g., "pff", "nfl_combine"
    STAGING_TABLE_NAME: str = None  # e.g., "pff_staging"
    
    # Validation thresholds
    DEFAULT_MIN_CONFIDENCE: float = 0.5
    DEFAULT_MIN_SAMPLE_SIZE: int = 0
    
    def __init__(self, db_session, extraction_id: UUID, logger_instance=None):
        """
        Initialize transformer.
        
        Args:
            db_session: Database session for querying/inserting
            extraction_id: UUID for this ETL pipeline run
            logger_instance: Optional logger (defaults to module logger)
        """
        if not self.SOURCE_NAME:
            raise ValueError(f"{self.__class__.__name__} must set SOURCE_NAME")
        if not self.STAGING_TABLE_NAME:
            raise ValueError(f"{self.__class__.__name__} must set STAGING_TABLE_NAME")
        
        self.db = db_session
        self.extraction_id = extraction_id
        self.logger = logger_instance or logging.getLogger(self.__class__.__name__)
        self.source_name = self.SOURCE_NAME
        self.staging_table = self.STAGING_TABLE_NAME
        
        # Statistics
        self.stats = {
            'validated': 0,
            'invalid': 0,
            'matched': 0,
            'new_prospects': 0,
            'conflicts': 0,
            'errors': 0,
        }
    
    # ========== ABSTRACT METHODS (Subclasses Must Implement) ==========
    
    @abstractmethod
    async def validate_staging_data(self, staging_row: Dict) -> bool:
        """
        Validate raw staging data.
        
        Return True if valid, False if should be skipped.
        Log warnings/errors for each validation failure.
        
        Args:
            staging_row: Row from staging table
            
        Returns:
            bool: True if valid, False otherwise
            
        Example:
            async def validate_staging_data(self, row: Dict) -> bool:
                if not row.get('pff_id'):
                    self.logger.warning(f"Row {row['id']}: missing pff_id")
                    return False
                if not (0 <= row.get('overall_grade', 0) <= 100):
                    self.logger.warning(f"Row {row['id']}: grade out of range")
                    return False
                return True
        """
        pass
    
    @abstractmethod
    async def get_prospect_identity(self, staging_row: Dict) -> Optional[Dict]:
        """
        Extract prospect identity from staging row.
        
        Return dict with prospect identifiers or None if unrecognizable.
        
        Args:
            staging_row: Row from staging table
            
        Returns:
            dict with keys like {pff_id, name_first, name_last, position, college, ...}
            or None if prospect cannot be identified
            
        Example:
            async def get_prospect_identity(self, row: Dict) -> Optional[Dict]:
                return {
                    'pff_id': row['pff_id'],
                    'name_first': row.get('first_name', '').strip(),
                    'name_last': row.get('last_name', '').strip(),
                    'position': row.get('position'),
                    'college': row.get('college'),
                }
        """
        pass
    
    @abstractmethod
    async def transform_staging_to_canonical(
        self, staging_row: Dict, prospect_id: UUID
    ) -> TransformationResult:
        """
        Transform single staging row to canonical fields.
        
        Perform all normalization, unit conversion, etc.
        Record complete lineage for all changes.
        
        Args:
            staging_row: Row from staging table
            prospect_id: UUID of matched/created prospect_core
            
        Returns:
            TransformationResult with field changes and lineage records
            
        Example:
            async def transform_staging_to_canonical(
                self, staging_row: Dict, prospect_id: UUID
            ) -> TransformationResult:
                raw_grade = staging_row['overall_grade']
                normalized_grade = self._normalize_grade(raw_grade)
                
                return TransformationResult(
                    entity_id=prospect_id,
                    entity_type='prospect_grades',
                    field_changes=[
                        FieldChange(
                            field_name='grade_normalized',
                            value_current=normalized_grade,
                            value_previous=None,
                            transformation_rule_id='pff_grade_normalize',
                            transformation_logic=f"grade = 5.0 + (raw / 100 * 5.0)"
                        )
                    ],
                    extraction_id=self.extraction_id,
                    source_system=self.source_name,
                    source_row_id=staging_row['id'],
                    staged_from_table=self.staging_table,
                )
        """
        pass
    
    # ========== COMMON TRANSFORMATION METHODS ==========
    
    async def process_staging_batch(
        self, staging_rows: List[Dict]
    ) -> Tuple[List[TransformationResult], List[Dict]]:
        """
        Process batch of staging rows through complete transformation pipeline.
        
        Returns (successes, failures) for monitoring and error handling.
        
        Args:
            staging_rows: List of rows from staging table
            
        Returns:
            Tuple of:
            - List[TransformationResult]: Successfully transformed rows
            - List[Dict]: Failed rows with failure info
        """
        successes = []
        failures = []
        
        self.logger.info(f"Starting batch transformation: {len(staging_rows)} rows from {self.source_name}")
        
        for row in staging_rows:
            try:
                # Phase 1: Validate
                if not await self.validate_staging_data(row):
                    self.stats['invalid'] += 1
                    failures.append({
                        'staging_id': row.get('id'),
                        'phase': TransformationPhase.VALIDATE,
                        'reason': 'validation_failed',
                        'source_system': self.source_name,
                    })
                    continue
                
                self.stats['validated'] += 1
                
                # Phase 2: Extract Identity
                prospect_identity = await self.get_prospect_identity(row)
                if not prospect_identity:
                    self.stats['invalid'] += 1
                    self.logger.warning(f"Row {row.get('id')}: could not extract prospect identity")
                    failures.append({
                        'staging_id': row.get('id'),
                        'phase': TransformationPhase.MATCH,
                        'reason': 'prospect_identity_not_found',
                        'source_system': self.source_name,
                    })
                    continue
                
                # Phase 3: Match or Create Prospect
                prospect_id = await self._match_or_create_prospect(prospect_identity, row)
                if prospect_id:
                    self.stats['matched'] += 1
                else:
                    self.logger.error(f"Row {row.get('id')}: failed to match/create prospect")
                    self.stats['errors'] += 1
                    failures.append({
                        'staging_id': row.get('id'),
                        'phase': TransformationPhase.MATCH,
                        'reason': 'prospect_match_failed',
                        'source_system': self.source_name,
                    })
                    continue
                
                # Phase 4: Transform to Canonical
                result = await self.transform_staging_to_canonical(row, prospect_id)
                
                if result.had_conflicts:
                    self.stats['conflicts'] += 1
                
                successes.append(result)
                
            except ValidationError as e:
                self.logger.warning(f"Row {row.get('id')}: validation error: {e}")
                self.stats['invalid'] += 1
                failures.append({
                    'staging_id': row.get('id'),
                    'phase': TransformationPhase.VALIDATE,
                    'reason': 'validation_exception',
                    'error': str(e),
                    'source_system': self.source_name,
                })
            except Exception as e:
                self.logger.error(f"Row {row.get('id')}: transformation error: {e}", exc_info=True)
                self.stats['errors'] += 1
                failures.append({
                    'staging_id': row.get('id'),
                    'phase': TransformationPhase.NORMALIZE,
                    'reason': 'transformation_exception',
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'source_system': self.source_name,
                })
        
        self.logger.info(
            f"Batch complete: {len(successes)} succeeded, {len(failures)} failed. "
            f"Stats: {self.stats}"
        )
        
        return successes, failures
    
    async def _match_or_create_prospect(
        self, identity: Dict, staging_row: Dict
    ) -> Optional[UUID]:
        """
        Match staging prospect to existing prospect_core or create new.
        
        This is a template method that can be overridden by subclasses
        for source-specific matching logic.
        
        Default implementation:
        1. Try exact match on source_id (pff_id, etc.)
        2. Try fuzzy match on name + position + college
        3. Create new prospect if no match
        
        Args:
            identity: Dict from get_prospect_identity()
            staging_row: Original staging row (for creating new prospect)
            
        Returns:
            UUID of matched/created prospect_core, or None on error
        """
        # This should be implemented by subclasses
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement _match_or_create_prospect()"
        )
    
    # ========== UTILITY METHODS FOR TRANSFORMATIONS ==========
    
    def validate_field(
        self,
        field_name: str,
        value: Any,
        allowed_type: type,
        min_value: Optional[Any] = None,
        max_value: Optional[Any] = None,
        allowed_values: Optional[List] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate a single field.
        
        Args:
            field_name: Name of field for logging
            value: Value to validate
            allowed_type: Expected type (str, int, float, etc.)
            min_value: Minimum value (for numeric fields)
            max_value: Maximum value (for numeric fields)
            allowed_values: List of allowed values (for enums)
            
        Returns:
            (is_valid, error_message)
            
        Example:
            is_valid, error = self.validate_field(
                'overall_grade', 87.5, float, min_value=0, max_value=100
            )
            if not is_valid:
                raise ValidationError(f"Grade: {error}")
        """
        if value is None:
            return True, None  # NULL is valid
        
        if not isinstance(value, allowed_type):
            return False, f"{field_name} must be {allowed_type.__name__}, got {type(value).__name__}"
        
        if allowed_values and value not in allowed_values:
            return False, f"{field_name} must be one of {allowed_values}, got {value}"
        
        if min_value is not None and value < min_value:
            return False, f"{field_name} must be >= {min_value}, got {value}"
        
        if max_value is not None and value > max_value:
            return False, f"{field_name} must be <= {max_value}, got {value}"
        
        return True, None
    
    def create_field_change(
        self,
        field_name: str,
        new_value: Any,
        old_value: Optional[Any] = None,
        transformation_rule_id: str = "",
        transformation_logic: str = "",
    ) -> FieldChange:
        """
        Create a FieldChange record for lineage tracking.
        
        Args:
            field_name: Name of the field that changed
            new_value: New value
            old_value: Previous value (optional)
            transformation_rule_id: ID of rule that transformed this
            transformation_logic: Human-readable description of transformation
            
        Returns:
            FieldChange object
        """
        return FieldChange(
            field_name=field_name,
            value_current=new_value,
            value_previous=old_value,
            transformation_rule_id=transformation_rule_id,
            transformation_logic=transformation_logic,
        )
    
    def record_conflict(
        self,
        field_name: str,
        resolved_value: Any,
        conflicting_sources: Dict[str, Any],
        resolution_rule: str,
    ) -> FieldChange:
        """
        Record a field where multiple sources provided different values.
        
        Args:
            field_name: Name of field with conflict
            resolved_value: Value that was chosen
            conflicting_sources: {source_name: value, ...}
            resolution_rule: How conflict was resolved (priority_order, most_recent, etc.)
            
        Returns:
            FieldChange with conflict info
        """
        return FieldChange(
            field_name=field_name,
            value_current=resolved_value,
            had_conflict=True,
            conflicting_sources=conflicting_sources,
            conflict_resolution_rule=resolution_rule,
        )
    
    def get_stats(self) -> Dict[str, int]:
        """Return transformation statistics"""
        return self.stats.copy()
    
    def log_summary(self):
        """Log summary statistics for this transformation batch"""
        self.logger.info(
            f"{self.source_name} transformation summary: "
            f"validated={self.stats['validated']}, "
            f"matched={self.stats['matched']}, "
            f"conflicts={self.stats['conflicts']}, "
            f"errors={self.stats['errors']}"
        )
