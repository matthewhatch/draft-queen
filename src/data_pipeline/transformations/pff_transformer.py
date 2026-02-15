"""PFF Transformer - Transform PFF staging data to prospect grades

Transforms raw PFF grades from staging tables to canonical prospect_grades table.

Key responsibilities:
1. Validate PFF staging data (grades within 0-100, required fields present)
2. Extract prospect identity from PFF data
3. Normalize grades from 0-100 scale to 5.0-10.0 scale
4. Match or create prospect_core record
5. Record transformation lineage

Grade Normalization:
- PFF uses 0-100 scale (e.g., 75 = good player)
- Canonical scale is 5.0-10.0 (e.g., 7.5 = good player)
- Linear transformation: grade_normalized = (grade_raw / 100) * 5 + 5
- Examples:
  - 0 → 5.0 (worst)
  - 50 → 7.5 (average)
  - 100 → 10.0 (best)

Prospect Matching Strategy:
1. Primary: pff_id (exact match on prospect_core.pff_id)
2. Secondary: Fuzzy name match (if no pff_id in system yet)
3. Fallback: Create new prospect_core record
"""

from typing import Dict, Optional, Tuple
from uuid import UUID
import logging
from decimal import Decimal
from datetime import datetime

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from .base_transformer import (
    BaseTransformer,
    TransformationResult,
    FieldChange,
    ValidationError,
)

logger = logging.getLogger(__name__)


class PFFTransformer(BaseTransformer):
    """Transform PFF staging data to prospect grades.
    
    Attributes:
        SOURCE_NAME: 'PFF' - identifies this transformer as PFF source
        STAGING_TABLE_NAME: 'pff_staging' - source staging table
        session: Database session for prospect_core queries
        extraction_id: UUID identifying this extraction batch
    """

    SOURCE_NAME = 'PFF'
    STAGING_TABLE_NAME = 'pff_staging'

    async def validate_staging_data(self, row: Dict) -> bool:
        """Validate PFF staging row has required fields and valid values.
        
        Args:
            row: PFF staging row from database
            
        Returns:
            bool: True if row is valid, False otherwise
            
        Raises:
            ValidationError: If required fields are missing (caught by caller)
        """
        try:
            # Required fields
            if not row.get('pff_id'):
                self.logger.warning(f"Missing pff_id in row {row.get('id')}")
                return False
            
            if not row.get('first_name') or not row.get('last_name'):
                self.logger.warning(f"Missing name fields for pff_id {row.get('pff_id')}")
                return False
            
            if not row.get('position'):
                self.logger.warning(f"Missing position for pff_id {row.get('pff_id')}")
                return False
            
            if not row.get('college'):
                self.logger.warning(f"Missing college for pff_id {row.get('pff_id')}")
                return False
            
            # Grade validation (0-100 scale)
            # overall_grade is required; position_grade is optional
            if row.get('overall_grade') is None:
                self.logger.warning(f"Missing overall_grade for pff_id {row.get('pff_id')}")
                return False
            
            # Validate grade is within 0-100 range
            overall_grade = float(row['overall_grade'])
            is_valid, error_msg = self.validate_field(
                'overall_grade',
                overall_grade,
                float,
                min_value=0.0,
                max_value=100.0
            )
            if not is_valid:
                self.logger.warning(f"Invalid grade {overall_grade} for pff_id {row.get('pff_id')}: {error_msg}")
                return False
            
            # Optional position_grade validation if present
            if row.get('position_grade') is not None:
                position_grade = float(row['position_grade'])
                is_valid, error_msg = self.validate_field(
                    'position_grade',
                    position_grade,
                    float,
                    min_value=0.0,
                    max_value=100.0
                )
                if not is_valid:
                    self.logger.warning(f"Invalid position_grade {position_grade} for pff_id {row.get('pff_id')}")
                    return False
            
            self.stats['validated'] += 1
            return True
            
        except Exception as e:
            self.logger.error(f"Validation error for pff_id {row.get('pff_id')}: {str(e)}")
            self.stats['errors'] += 1
            return False

    def get_prospect_identity(self, row: Dict) -> Dict:
        """Extract prospect identity fields from PFF staging data.
        
        Args:
            row: PFF staging row
            
        Returns:
            Dict with identifying fields for matching
        """
        return {
            'pff_id': row.get('pff_id'),
            'first_name': row.get('first_name'),
            'last_name': row.get('last_name'),
            'position': row.get('position'),
            'college': row.get('college'),
        }

    async def transform_staging_to_canonical(
        self,
        row: Dict,
        prospect_id: UUID
    ) -> TransformationResult:
        """Transform PFF staging row to prospect_grades record.
        
        Args:
            row: PFF staging data
            prospect_id: UUID of matched/created prospect in prospect_core
            
        Returns:
            TransformationResult with field changes and lineage records
        """
        field_changes = []
        
        # Overall Grade Transformation (0-100 → 5.0-10.0)
        grade_raw = float(row['overall_grade'])
        grade_normalized = self._normalize_grade(grade_raw)
        
        field_change = self.create_field_change(
            field_name='grade_normalized',
            new_value=grade_normalized,
            old_value=None,
            transformation_rule_id='pff_normalize_grade_linear',
        )
        field_changes.append(field_change)
        
        # Position Grade (if provided)
        if row.get('position_grade') is not None:
            position_grade_raw = float(row['position_grade'])
            position_grade_normalized = self._normalize_grade(position_grade_raw)
            
            field_change = self.create_field_change(
                field_name='position_grade',
                new_value=position_grade_normalized,
                old_value=None,
                transformation_rule_id='pff_normalize_position_grade',
            )
            field_changes.append(field_change)
        
        # Source System Tracking
        field_change = self.create_field_change(
            field_name='source',
            new_value='pff',
            old_value=None,
            transformation_rule_id='source_attribution',
        )
        field_changes.append(field_change)
        
        field_change = self.create_field_change(
            field_name='source_system_id',
            new_value=row.get('pff_id'),
            old_value=None,
            transformation_rule_id='pff_id_tracking',
        )
        field_changes.append(field_change)
        
        # Grade Metadata
        field_change = self.create_field_change(
            field_name='grade_raw',
            new_value=grade_raw,
            old_value=None,
            transformation_rule_id='raw_grade_capture',
        )
        field_changes.append(field_change)
        
        field_change = self.create_field_change(
            field_name='grade_raw_scale',
            new_value='0-100',
            old_value=None,
            transformation_rule_id='source_scale_identification',
        )
        field_changes.append(field_change)
        
        field_change = self.create_field_change(
            field_name='position_rated',
            new_value=row.get('position'),
            old_value=None,
            transformation_rule_id='position_capture',
        )
        field_changes.append(field_change)
        
        # Sample Size (snaps analyzed)
        if row.get('film_watched_snaps') is not None:
            field_change = self.create_field_change(
                field_name='sample_size',
                new_value=int(row['film_watched_snaps']),
                old_value=None,
                transformation_rule_id='sample_size_snaps',
            )
            field_changes.append(field_change)
        
        # Grade Issued Date
        if row.get('grade_issued_date') is not None:
            field_change = self.create_field_change(
                field_name='grade_issued_date',
                new_value=str(row['grade_issued_date']),
                old_value=None,
                transformation_rule_id='grade_date_capture',
            )
            field_changes.append(field_change)
        
        # Preliminary Status
        if row.get('grade_is_preliminary') is not None:
            field_change = self.create_field_change(
                field_name='grade_is_preliminary',
                new_value=row['grade_is_preliminary'],
                old_value=None,
                transformation_rule_id='preliminary_status',
            )
            field_changes.append(field_change)
        
        # Transformation Rules Metadata
        transformation_rules = {
            'normalization_method': 'linear',
            'grade_scale_input': '0-100',
            'grade_scale_output': '5.0-10.0',
            'formula': 'grade_normalized = (grade_raw / 100) * 5 + 5',
            'sample_size_field': 'film_watched_snaps',
        }
        
        field_change = self.create_field_change(
            field_name='transformation_rules',
            new_value=transformation_rules,
            old_value=None,
            transformation_rule_id='metadata_capture',
        )
        field_changes.append(field_change)
        
        return TransformationResult(
            entity_type='prospect_grades',
            entity_id=prospect_id,
            field_changes=field_changes,
            extraction_id=self.extraction_id,
            source_system='pff',
            source_row_id=row.get('id', 0),
            staged_from_table='pff_staging',
        )

    async def _match_or_create_prospect(self, identity_dict: Dict) -> UUID:
        """Find matching prospect or create new one.
        
        Matching Strategy:
        1. Try exact match on pff_id
        2. Try fuzzy name match if no exact match
        3. Create new prospect_core record
        
        Args:
            identity_dict: Dict with pff_id, first_name, last_name, position, college
            
        Returns:
            UUID of matched or created prospect
        """
        pff_id = identity_dict.get('pff_id')
        first_name = identity_dict.get('first_name')
        last_name = identity_dict.get('last_name')
        position = identity_dict.get('position')
        college = identity_dict.get('college')
        
        # Strategy 1: Exact match on pff_id
        if pff_id:
            result = self.db.execute(
                select(text('id')).select_from(text('prospect_core')).where(
                    text(f"pff_id = '{pff_id}'")
                )
            )
            match = result.scalar()
            if match:
                logger.info(f"Matched prospect {pff_id} to existing prospect_core.id={match}")
                self.stats['matched'] += 1
                return UUID(match) if isinstance(match, str) else match
        
        # Strategy 2: Try fuzzy name match (if no pff_id match)
        # This is a simplified exact match on name+position+college
        # In production, would use fuzzy matching library (fuzzywuzzy, difflib)
        result = self.db.execute(
            select(text('id')).select_from(text('prospect_core')).where(
                text(f"name_first = '{first_name}' AND name_last = '{last_name}' AND position = '{position}' AND college = '{college}'")
            )
        )
        match = result.scalar()
        if match:
            logger.info(f"Matched {first_name} {last_name} to existing prospect by name")
            # Update pff_id if it was empty
            if pff_id:
                self.db.execute(
                    text(f"UPDATE prospect_core SET pff_id = '{pff_id}' WHERE id = '{match}'")
                )
            self.stats['matched'] += 1
            return UUID(match) if isinstance(match, str) else match
        
        # Strategy 3: Create new prospect_core record
        logger.info(f"Creating new prospect_core for {first_name} {last_name} from PFF")
        new_prospect_id = UUID('00000000-0000-0000-0000-000000000000')  # Will be overridden by DB
        
        # Insert new prospect_core record
        insert_stmt = text(f"""
            INSERT INTO prospect_core 
            (name_first, name_last, position, college, pff_id, status, 
             created_from_source, primary_source, created_at, updated_at)
            VALUES ('{first_name}', '{last_name}', '{position}', '{college}', 
                   '{pff_id}', 'active', 'pff', 'pff', now(), now())
            RETURNING id
        """)
        result = self.db.execute(insert_stmt)
        new_prospect_id = result.scalar()
        
        self.stats['new_prospects'] += 1
        logger.info(f"Created new prospect {new_prospect_id} for {first_name} {last_name}")
        
        return UUID(new_prospect_id) if isinstance(new_prospect_id, str) else new_prospect_id

    @staticmethod
    def _normalize_grade(grade_raw: float) -> Decimal:
        """Normalize PFF grade from 0-100 scale to 5.0-10.0 scale.
        
        Linear transformation:
        - Input: 0-100 (PFF scale)
        - Output: 5.0-10.0 (canonical scale)
        - Formula: grade_normalized = (grade_raw / 100) * 5 + 5
        
        Examples:
        - 0 → 5.0 (worst possible)
        - 25 → 6.25
        - 50 → 7.5 (average)
        - 75 → 8.75
        - 100 → 10.0 (best possible)
        
        Args:
            grade_raw: Raw PFF grade (0-100)
            
        Returns:
            Decimal: Normalized grade (5.0-10.0)
        """
        if not isinstance(grade_raw, (int, float, Decimal)):
            raise ValueError(f"Grade must be numeric, got {type(grade_raw)}")
        
        # Clamp to valid range (defensive)
        grade_raw = max(0.0, min(100.0, float(grade_raw)))
        
        # Linear transformation
        normalized = (grade_raw / 100.0) * 5.0 + 5.0
        
        return Decimal(str(normalized)).quantize(Decimal('0.1'))


# Module exports
__all__ = ['PFFTransformer']
