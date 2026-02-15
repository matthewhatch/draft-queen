# ETL Implementation Guide: Multi-Source Data Architecture

**Date:** February 15, 2026  
**For:** Engineering Team  
**Purpose:** Practical guide to implementing ETL architecture with source-by-source breakdown

---

## Quick Overview

We're restructuring the data pipeline from a **monolithic loader** to an **enterprise ETL system** with:
- Source-specific staging tables (raw data capture)
- Canonical transformation layer (normalized business entities)
- Complete data lineage tracking (audit trail)

**Result:** Scalable, auditable, debuggable system for 5+ data sources

---

## Phase 1: Foundation Architecture (Weeks 1-2)

### Step 1.1: Create Base Staging & Canonical Tables

**File:** `migrations/versions/0012_etl_foundation.py`

```python
"""Create ETL foundation: staging tables + canonical models"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

def upgrade():
    # ========== STAGING TABLES (Raw Data) ==========
    
    # PFF Staging (Draft Grades)
    op.create_table(
        'pff_staging',
        sa.Column('id', sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column('extraction_id', UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('pff_id', sa.String(50), nullable=False),
        sa.Column('first_name', sa.String(255)),
        sa.Column('last_name', sa.String(255)),
        sa.Column('position', sa.String(10)),
        sa.Column('college', sa.String(255)),
        sa.Column('draft_year', sa.Integer),
        sa.Column('overall_grade', sa.Numeric(5, 2)),
        sa.Column('position_grade', sa.Numeric(5, 2)),
        sa.Column('height_inches', sa.Integer),
        sa.Column('weight_lbs', sa.Integer),
        sa.Column('arm_length_inches', sa.Numeric(3, 1)),
        sa.Column('hand_size_inches', sa.Numeric(3, 2)),
        sa.Column('film_watched_snaps', sa.Integer),
        sa.Column('grade_issued_date', sa.Date),
        sa.Column('raw_json_data', JSONB()),
        sa.Column('data_hash', sa.String(64)),
        sa.Column('extraction_timestamp', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('notes', sa.Text),
        sa.UniqueConstraint('pff_id', 'extraction_id', name='uq_pff_staging'),
        sa.Index('idx_pff_staging_extraction_id', 'extraction_id'),
        sa.Index('idx_pff_staging_draft_year', 'draft_year'),
    )
    
    # NFL Combine Staging
    op.create_table(
        'nfl_combine_staging',
        sa.Column('id', sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column('extraction_id', UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('nfl_combine_id', sa.String(50)),
        sa.Column('first_name', sa.String(255)),
        sa.Column('last_name', sa.String(255)),
        sa.Column('position', sa.String(10)),
        sa.Column('college', sa.String(255)),
        sa.Column('test_date', sa.Date),
        sa.Column('location', sa.String(100)),
        sa.Column('test_type', sa.String(50)),
        sa.Column('height_feet_inches', sa.String(10)),
        sa.Column('weight_lbs', sa.Numeric(5, 1)),
        sa.Column('forty_yard_dash', sa.Numeric(4, 3)),
        sa.Column('bench_press_reps', sa.Integer),
        sa.Column('vertical_jump_inches', sa.Numeric(5, 2)),
        sa.Column('broad_jump_inches', sa.Numeric(5, 2)),
        sa.Column('shuttle_run', sa.Numeric(4, 3)),
        sa.Column('three_cone_drill', sa.Numeric(4, 3)),
        sa.Column('arm_length_inches', sa.Numeric(3, 1)),
        sa.Column('hand_size_inches', sa.Numeric(3, 2)),
        sa.Column('wonderlic_score', sa.Integer),
        sa.Column('raw_json_data', JSONB()),
        sa.Column('data_hash', sa.String(64)),
        sa.Column('extraction_timestamp', sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint('nfl_combine_id', 'test_date', 'test_type', 
                           name='uq_nfl_combine_staging'),
        sa.Index('idx_nfl_combine_staging_extraction_id', 'extraction_id'),
    )
    
    # CFR Staging (College Stats)
    op.create_table(
        'cfr_staging',
        sa.Column('id', sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column('extraction_id', UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('cfr_player_id', sa.String(100)),
        sa.Column('cfr_player_url', sa.String(500)),
        sa.Column('first_name', sa.String(255)),
        sa.Column('last_name', sa.String(255)),
        sa.Column('college', sa.String(255)),
        sa.Column('position', sa.String(10)),
        sa.Column('season', sa.Integer, nullable=False),
        sa.Column('games_played', sa.Integer),
        sa.Column('games_started', sa.Integer),
        # Offensive stats...
        sa.Column('passing_yards', sa.Integer),
        sa.Column('passing_touchdowns', sa.Integer),
        sa.Column('interceptions', sa.Integer),
        sa.Column('rushing_yards', sa.Integer),
        sa.Column('rushing_touchdowns', sa.Integer),
        sa.Column('receiving_receptions', sa.Integer),
        sa.Column('receiving_yards', sa.Integer),
        sa.Column('receiving_touchdowns', sa.Integer),
        # Defensive stats...
        sa.Column('tackles', sa.Integer),
        sa.Column('sacks', sa.Numeric(5, 1)),
        sa.Column('forced_fumbles', sa.Integer),
        sa.Column('interceptions_defensive', sa.Integer),
        sa.Column('raw_html_hash', sa.String(64)),
        sa.Column('data_hash', sa.String(64)),
        sa.Column('extraction_timestamp', sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint('cfr_player_id', 'season', name='uq_cfr_staging'),
        sa.Index('idx_cfr_staging_extraction_id', 'extraction_id'),
        sa.Index('idx_cfr_staging_college_season', 'college', 'season'),
    )
    
    # ========== CANONICAL TABLES (Transformed) ==========
    
    # Prospect Core (Identity Hub)
    op.create_table(
        'prospect_core',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.func.gen_random_uuid()),
        sa.Column('name_first', sa.String(255), nullable=False),
        sa.Column('name_last', sa.String(255), nullable=False),
        sa.Column('position', sa.String(10), nullable=False),
        sa.Column('college', sa.String(255), nullable=False),
        sa.Column('recruit_year', sa.Integer),
        # Source IDs
        sa.Column('pff_id', sa.String(50), unique=True),
        sa.Column('nfl_combine_id', sa.String(50)),
        sa.Column('cfr_player_id', sa.String(100)),
        sa.Column('yahoo_id', sa.String(50)),
        # Status & Quality
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('data_quality_score', sa.Numeric(3, 2)),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_from_source', sa.String(100)),
        sa.UniqueConstraint('name_first', 'name_last', 'position', 'college',
                           name='uq_prospect_identity'),
        sa.Index('idx_prospect_core_position', 'position'),
        sa.Index('idx_prospect_core_data_quality', 'data_quality_score'),
        sa.Index('idx_prospect_core_pff_id', 'pff_id'),
    )
    
    # ========== LINEAGE TABLE (Audit Trail) ==========
    
    op.create_table(
        'data_lineage',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.func.gen_random_uuid()),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('entity_id', UUID(as_uuid=True), nullable=False),
        sa.Column('field_name', sa.String(100), nullable=False),
        sa.Column('value_current', sa.Text),
        sa.Column('value_previous', sa.Text),
        sa.Column('extraction_id', UUID(as_uuid=True)),
        sa.Column('source_table', sa.String(100)),
        sa.Column('source_row_id', sa.BigInteger()),
        sa.Column('source_system', sa.String(50)),
        sa.Column('transformation_rule_id', sa.String(100)),
        sa.Column('transformation_logic', sa.Text),
        sa.Column('had_conflict', sa.Boolean(), default=False),
        sa.Column('conflicting_sources', JSONB()),
        sa.Column('conflict_resolution_rule', sa.String(100)),
        sa.Column('changed_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('changed_by', sa.String(100), default='system'),
        sa.Column('change_reason', sa.Text),
        sa.Index('idx_lineage_entity', 'entity_type', 'entity_id'),
        sa.Index('idx_lineage_source_system', 'source_system'),
        sa.Index('idx_lineage_changed_at', 'changed_at'),
    )

def downgrade():
    op.drop_table('data_lineage')
    op.drop_table('prospect_core')
    op.drop_table('cfr_staging')
    op.drop_table('nfl_combine_staging')
    op.drop_table('pff_staging')
```

### Step 1.2: Create Base Transformer Framework

**File:** `src/data_pipeline/transformations/base_transformer.py`

```python
"""Base classes for source-specific transformers"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from uuid import UUID
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class TransformationResult:
    """Result of transforming staging data to canonical form"""
    entity_id: UUID
    entity_type: str
    field_changes: Dict[str, Any]           # {field: new_value}
    lineage_records: List[Dict]             # Records for data_lineage table
    had_conflicts: bool = False
    conflict_resolution: Dict = None

class BaseTransformer(ABC):
    """
    Abstract base for source-specific transformers.
    
    Subclasses implement:
    - validate_staging_data()
    - transform_staging_to_canonical()
    - get_prospect_identity()
    """
    
    def __init__(self, db_session, pipeline_run_id: UUID):
        self.db = db_session
        self.pipeline_run_id = pipeline_run_id
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    async def validate_staging_data(self, staging_row: Dict) -> bool:
        """
        Validate raw staging data.
        Return True if valid, False if should be skipped.
        Log warnings/errors for each validation failure.
        """
        pass
    
    @abstractmethod
    async def get_prospect_identity(self, staging_row: Dict) -> Optional[str]:
        """
        Extract prospect identity from staging row.
        Return source-specific ID or None if unrecognizable.
        """
        pass
    
    @abstractmethod
    async def transform_staging_to_canonical(
        self, staging_row: Dict, prospect_id: UUID
    ) -> TransformationResult:
        """
        Transform single staging row to canonical fields.
        Handle normalization, unit conversion, etc.
        Record complete lineage.
        """
        pass
    
    async def process_staging_batch(
        self, staging_rows: List[Dict]
    ) -> tuple[List[TransformationResult], List[Dict]]:
        """
        Process batch of staging rows.
        Return (successes, failures) for monitoring.
        """
        successes = []
        failures = []
        
        for row in staging_rows:
            try:
                # Validate
                if not await self.validate_staging_data(row):
                    failures.append({
                        'staging_id': row['id'],
                        'reason': 'validation_failed'
                    })
                    continue
                
                # Get prospect identity
                prospect_identity = await self.get_prospect_identity(row)
                if not prospect_identity:
                    failures.append({
                        'staging_id': row['id'],
                        'reason': 'prospect_identity_not_found'
                    })
                    continue
                
                # Match to prospect_core or create new
                prospect_id = await self._match_or_create_prospect(
                    prospect_identity, row
                )
                
                # Transform
                result = await self.transform_staging_to_canonical(row, prospect_id)
                successes.append(result)
                
            except Exception as e:
                self.logger.error(f"Transformation failed for row {row.get('id')}: {e}")
                failures.append({
                    'staging_id': row['id'],
                    'reason': str(e),
                    'error_type': type(e).__name__
                })
        
        return successes, failures
    
    async def _match_or_create_prospect(
        self, identity: Dict, staging_row: Dict
    ) -> UUID:
        """
        Try to match staging prospect to existing prospect_core.
        If no match, create new prospect_core.
        """
        # Implementation in subclasses
        raise NotImplementedError
```

### Step 1.3: Create Lineage Recorder

**File:** `src/data_pipeline/transformations/lineage_recorder.py`

```python
"""Records data lineage for audit trail"""

from uuid import UUID
from typing import Dict, Any, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class LineageRecorder:
    """
    Records complete journey of every field:
    source → staging → transformation → canonical
    """
    
    def __init__(self, db_session):
        self.db = db_session
    
    async def record_field_transformation(
        self,
        entity_type: str,
        entity_id: UUID,
        field_name: str,
        new_value: Any,
        previous_value: Any,
        staging_row_id: int,
        source_system: str,
        transformation_rule_id: str,
        transformation_logic: str,
        had_conflict: bool = False,
        conflicting_values: Dict = None,
        conflict_resolution_rule: str = None,
        changed_by: str = 'system',
    ):
        """Record single field transformation"""
        
        lineage_record = {
            'id': uuid.uuid4(),
            'entity_type': entity_type,
            'entity_id': entity_id,
            'field_name': field_name,
            'value_current': str(new_value),
            'value_previous': str(previous_value) if previous_value else None,
            'source_table': f'{source_system}_staging',
            'source_row_id': staging_row_id,
            'source_system': source_system,
            'transformation_rule_id': transformation_rule_id,
            'transformation_logic': transformation_logic,
            'had_conflict': had_conflict,
            'conflicting_sources': conflicting_values,
            'conflict_resolution_rule': conflict_resolution_rule,
            'changed_at': datetime.utcnow(),
            'changed_by': changed_by,
        }
        
        await self.db.execute(
            """INSERT INTO data_lineage 
               (id, entity_type, entity_id, field_name, value_current, value_previous,
                source_table, source_row_id, source_system, transformation_rule_id,
                transformation_logic, had_conflict, conflicting_sources, 
                conflict_resolution_rule, changed_at, changed_by)
               VALUES (:id, :entity_type, :entity_id, :field_name, :value_current, 
                       :value_previous, :source_table, :source_row_id, :source_system,
                       :transformation_rule_id, :transformation_logic, :had_conflict,
                       :conflicting_sources, :conflict_resolution_rule, :changed_at,
                       :changed_by)""",
            lineage_record
        )
        
        logger.debug(
            f"Lineage recorded for {entity_type}:{entity_id}.{field_name} "
            f"from {source_system}"
        )
```

---

## Phase 2: Source Transformers (Weeks 2-3)

### Step 2.1: Implement PFF Transformer

**File:** `src/data_pipeline/transformations/pff_transformer.py`

```python
"""Transform PFF staging data to canonical grades"""

from typing import Optional, Dict, Any
from uuid import UUID
from difflib import SequenceMatcher
from .base_transformer import BaseTransformer, TransformationResult
from .lineage_recorder import LineageRecorder
import logging

logger = logging.getLogger(__name__)

class PFFTransformer(BaseTransformer):
    """Transform raw PFF grades to prospect_grades table"""
    
    GRADE_NORMALIZATION_CURVE = {
        # PFF uses 0-100; we normalize to 5.0-10.0
        # Distribution: 0-20 → 5.0-6.0, 40-60 → 7.0-8.0, 80-100 → 9.0-10.0
        'min_raw': 0,
        'max_raw': 100,
        'min_normalized': 5.0,
        'max_normalized': 10.0,
    }
    
    async def validate_staging_data(self, row: Dict) -> bool:
        """Validate PFF staging row"""
        
        # Required fields
        if not row.get('pff_id'):
            self.logger.warning(f"PFF staging row {row['id']}: missing pff_id")
            return False
        
        if row.get('overall_grade') is None:
            self.logger.warning(f"PFF staging row {row['id']}: missing overall_grade")
            return False
        
        # Grade range check
        if not (0 <= row['overall_grade'] <= 100):
            self.logger.warning(
                f"PFF staging row {row['id']}: grade {row['overall_grade']} "
                f"outside valid range [0, 100]"
            )
            return False
        
        # Position validation
        valid_positions = ['QB', 'RB', 'WR', 'TE', 'OL', 'DL', 'EDGE', 'LB', 'DB']
        if row.get('position') not in valid_positions:
            self.logger.warning(
                f"PFF staging row {row['id']}: invalid position {row['position']}"
            )
            return False
        
        return True
    
    async def get_prospect_identity(self, row: Dict) -> Optional[Dict]:
        """Extract prospect identity from PFF staging"""
        
        return {
            'pff_id': row['pff_id'],
            'name_first': row.get('first_name', '').strip(),
            'name_last': row.get('last_name', '').strip(),
            'position': row.get('position'),
            'college': row.get('college'),
        }
    
    async def _match_or_create_prospect(
        self, identity: Dict, staging_row: Dict
    ) -> UUID:
        """Match PFF prospect to existing prospect_core or create"""
        
        # PFF is authoritative on identity; if pff_id exists, use it
        existing = await self.db.fetch_one(
            "SELECT id FROM prospect_core WHERE pff_id = :pff_id",
            {'pff_id': identity['pff_id']}
        )
        
        if existing:
            return existing['id']
        
        # Try fuzzy match on name + college + position
        candidates = await self.db.fetch(
            """SELECT id, name_first, name_last FROM prospect_core 
               WHERE college = :college AND position = :position""",
            {
                'college': identity['college'],
                'position': identity['position'],
            }
        )
        
        best_match = None
        best_score = 0
        
        for candidate in candidates:
            name_score = self._name_similarity(
                f"{identity['name_first']} {identity['name_last']}",
                f"{candidate['name_first']} {candidate['name_last']}"
            )
            
            if name_score > 0.85:
                if name_score > best_score:
                    best_match = candidate
                    best_score = name_score
        
        if best_match:
            # Update PFF ID on existing prospect
            await self.db.execute(
                "UPDATE prospect_core SET pff_id = :pff_id WHERE id = :id",
                {'pff_id': identity['pff_id'], 'id': best_match['id']}
            )
            return best_match['id']
        
        # Create new prospect_core
        new_prospect_id = await self.db.execute(
            """INSERT INTO prospect_core 
               (name_first, name_last, position, college, pff_id, 
                created_from_source, status)
               VALUES (:name_first, :name_last, :position, :college, :pff_id,
                       'pff', 'active')
               RETURNING id""",
            {
                'name_first': identity['name_first'],
                'name_last': identity['name_last'],
                'position': identity['position'],
                'college': identity['college'],
                'pff_id': identity['pff_id'],
            }
        )
        
        return new_prospect_id
    
    async def transform_staging_to_canonical(
        self, staging_row: Dict, prospect_id: UUID
    ) -> TransformationResult:
        """Transform PFF staging to prospect_grades"""
        
        # Normalize grade
        raw_grade = staging_row['overall_grade']
        normalized_grade = self._normalize_grade(raw_grade)
        
        lineage_recorder = LineageRecorder(self.db)
        
        # Record lineage
        await lineage_recorder.record_field_transformation(
            entity_type='prospect_grade',
            entity_id=prospect_id,  # Will be replaced with actual grade ID
            field_name='grade_normalized',
            new_value=normalized_grade,
            previous_value=None,
            staging_row_id=staging_row['id'],
            source_system='pff',
            transformation_rule_id='pff_grade_normalization_curve',
            transformation_logic=(
                f"grade_normalized = 5.0 + (raw_grade / 100.0 * 5.0) "
                f"where raw_grade = {raw_grade}"
            ),
        )
        
        return TransformationResult(
            entity_id=prospect_id,
            entity_type='prospect_grade',
            field_changes={
                'prospect_id': prospect_id,
                'source': 'pff',
                'source_system_id': staging_row['pff_id'],
                'grade_raw': raw_grade,
                'grade_raw_scale': '0-100',
                'grade_normalized': normalized_grade,
                'position_rated': staging_row.get('position'),
                'sample_size': staging_row.get('film_watched_snaps'),
                'grade_issued_date': staging_row.get('grade_issued_date'),
                'analyst_name': staging_row.get('analyst_name'),
                'transformation_rules': {
                    'normalization_method': 'curve_linear',
                    'applied_rules': ['grade_range_check', 'position_validation'],
                },
            },
            lineage_records=[],  # Already recorded
        )
    
    @staticmethod
    def _normalize_grade(raw_grade: float) -> float:
        """Normalize 0-100 grade to 5.0-10.0 scale"""
        # Simple linear: 0→5.0, 100→10.0
        return 5.0 + (raw_grade / 100.0 * 5.0)
    
    @staticmethod
    def _name_similarity(name1: str, name2: str) -> float:
        """Calculate name similarity ratio"""
        return SequenceMatcher(None, name1.upper(), name2.upper()).ratio()
```

### Step 2.2: Implement CFR Transformer

**File:** `src/data_pipeline/transformations/cfr_transformer.py`

```python
"""Transform CFR staging data to prospect_college_stats"""

from typing import Optional, Dict, Any
from uuid import UUID
from .base_transformer import BaseTransformer, TransformationResult
from .lineage_recorder import LineageRecorder
import logging

logger = logging.getLogger(__name__)

class CFRTransformer(BaseTransformer):
    """Transform raw CFR college stats to prospect_college_stats table"""
    
    # Position-specific stat grouping
    POSITION_STAT_GROUPS = {
        'QB': [
            'passing_attempts', 'passing_completions', 'passing_yards',
            'passing_touchdowns', 'interceptions', 'rushing_attempts', 'rushing_yards'
        ],
        'RB': [
            'rushing_attempts', 'rushing_yards', 'rushing_touchdowns',
            'receiving_receptions', 'receiving_yards', 'receiving_touchdowns'
        ],
        'WR': [
            'receiving_targets', 'receiving_receptions', 'receiving_yards',
            'receiving_touchdowns', 'rushing_attempts', 'rushing_yards'
        ],
        'TE': [
            'receiving_targets', 'receiving_receptions', 'receiving_yards',
            'receiving_touchdowns'
        ],
        'DL': [
            'tackles', 'sacks', 'tackles_for_loss', 'forced_fumbles'
        ],
        'EDGE': [
            'sacks', 'tackles_for_loss', 'tackles', 'forced_fumbles'
        ],
        'LB': [
            'tackles', 'sacks', 'tackles_for_loss', 'passes_defended',
            'interceptions_defensive'
        ],
        'DB': [
            'passes_defended', 'interceptions_defensive', 'tackles'
        ],
        'OL': [
            'games_started',
        ]
    }
    
    async def validate_staging_data(self, row: Dict) -> bool:
        """Validate CFR staging row"""
        
        # Required fields
        if not row.get('cfr_player_id'):
            self.logger.warning(f"CFR staging row {row['id']}: missing cfr_player_id")
            return False
        
        if row.get('season') is None:
            self.logger.warning(f"CFR staging row {row['id']}: missing season")
            return False
        
        # Season range
        if not (2020 <= row['season'] <= 2025):
            self.logger.warning(
                f"CFR staging row {row['id']}: season {row['season']} "
                f"outside expected range"
            )
            return False
        
        # At least some stats provided
        stat_fields = [k for k in row.keys() if 'yards' in k or 'attempts' in k]
        if not stat_fields:
            self.logger.warning(
                f"CFR staging row {row['id']}: no stat fields found"
            )
            return False
        
        return True
    
    async def get_prospect_identity(self, row: Dict) -> Optional[Dict]:
        """Extract prospect identity from CFR staging"""
        
        return {
            'cfr_player_id': row['cfr_player_id'],
            'name_first': row.get('first_name', '').strip(),
            'name_last': row.get('last_name', '').strip(),
            'position': row.get('position'),
            'college': row.get('college'),
        }
    
    async def _match_or_create_prospect(
        self, identity: Dict, staging_row: Dict
    ) -> UUID:
        """Match CFR prospect to existing prospect_core"""
        
        # CFR doesn't have as authoritative matching as PFF
        # Try matching by name + college + position
        
        candidates = await self.db.fetch(
            """SELECT id, name_first, name_last FROM prospect_core 
               WHERE college = :college AND position = :position""",
            {'college': identity['college'], 'position': identity['position']}
        )
        
        best_match = None
        best_score = 0
        
        for candidate in candidates:
            score = self._name_similarity(
                f"{identity['name_first']} {identity['name_last']}",
                f"{candidate['name_first']} {candidate['name_last']}"
            )
            if score > best_score:
                best_match = candidate
                best_score = score
        
        if best_match and best_score > 0.80:
            await self.db.execute(
                "UPDATE prospect_core SET cfr_player_id = :cfr_id WHERE id = :id",
                {'cfr_id': identity['cfr_player_id'], 'id': best_match['id']}
            )
            return best_match['id']
        
        # Create new prospect if no good match
        if best_score < 0.80:
            new_prospect_id = await self.db.execute(
                """INSERT INTO prospect_core 
                   (name_first, name_last, position, college, cfr_player_id,
                    created_from_source, status)
                   VALUES (:name_first, :name_last, :position, :college, :cfr_id,
                           'cfr', 'active')
                   RETURNING id""",
                {
                    'name_first': identity['name_first'],
                    'name_last': identity['name_last'],
                    'position': identity['position'],
                    'college': identity['college'],
                    'cfr_id': identity['cfr_player_id'],
                }
            )
            return new_prospect_id
        
        raise ValueError(f"Could not match CFR prospect: {identity}")
    
    async def transform_staging_to_canonical(
        self, staging_row: Dict, prospect_id: UUID
    ) -> TransformationResult:
        """Transform CFR staging to prospect_college_stats"""
        
        position = staging_row.get('position', 'UNKNOWN')
        expected_stats = self.POSITION_STAT_GROUPS.get(position, [])
        
        # Collect position-specific stats
        field_changes = {
            'prospect_id': prospect_id,
            'season': staging_row['season'],
            'college': staging_row.get('college'),
            'games_played': staging_row.get('games_played'),
            'games_started': staging_row.get('games_started'),
        }
        
        # Add available stats
        for stat in expected_stats:
            if stat in staging_row:
                field_changes[stat] = staging_row[stat]
        
        # Calculate data completeness
        completeness = len([v for v in field_changes.values() if v is not None]) / len(field_changes)
        
        field_changes['data_sources'] = ['cfr']
        field_changes['data_completeness'] = completeness
        
        return TransformationResult(
            entity_id=prospect_id,
            entity_type='prospect_college_stats',
            field_changes=field_changes,
            lineage_records=[],
        )
```

---

## Phase 3: Orchestration (Weeks 3-4)

### Step 3.1: Create ETL Orchestrator

**File:** `src/data_pipeline/orchestration/etl_pipeline.py`

```python
"""Main ETL pipeline orchestrator"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Tuple
from uuid import UUID
import logging

from ..extractors import PFFExtractor, CFRExtractor, NFLCombineExtractor
from ..transformations import PFFTransformer, CFRTransformer, NFLCombineTransformer
from ..models import ProspectCore, ProspectGrade, ProspectCollegeStats

logger = logging.getLogger(__name__)

class MultiSourceETLPipeline:
    """Enterprise ETL pipeline for multi-source prospect data"""
    
    def __init__(self, db_session):
        self.db = db_session
        self.extractors = {
            'pff': PFFExtractor(db_session),
            'cfr': CFRExtractor(db_session),
            'nfl_combine': NFLCombineExtractor(db_session),
        }
        self.transformers = {
            'pff': PFFTransformer(db_session, None),  # run_id set per run
            'cfr': CFRTransformer(db_session, None),
            'nfl_combine': NFLCombineTransformer(db_session, None),
        }
    
    async def run_daily_pipeline(self) -> Dict:
        """Execute full ETL pipeline"""
        
        pipeline_run_id = uuid.uuid4()
        start_time = datetime.utcnow()
        
        logger.info(f"[{pipeline_run_id}] Starting daily ETL pipeline")
        
        try:
            # =============== EXTRACT PHASE ===============
            logger.info(f"[{pipeline_run_id}] Starting extraction phase")
            extractions = await self._extract_phase(pipeline_run_id)
            
            # =============== STAGE PHASE ===============
            logger.info(f"[{pipeline_run_id}] Starting staging phase")
            staging_results = await self._stage_phase(pipeline_run_id, extractions)
            
            # =============== TRANSFORM PHASE ===============
            logger.info(f"[{pipeline_run_id}] Starting transformation phase")
            transformation_results = await self._transform_phase(pipeline_run_id)
            
            # =============== LOAD PHASE ===============
            logger.info(f"[{pipeline_run_id}] Starting load phase")
            load_results = await self._load_phase(pipeline_run_id, transformation_results)
            
            # =============== PUBLISH PHASE ===============
            logger.info(f"[{pipeline_run_id}] Starting publish phase")
            await self._publish_phase(pipeline_run_id)
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            logger.info(
                f"[{pipeline_run_id}] Pipeline completed successfully "
                f"in {duration:.2f}s"
            )
            
            return {
                'status': 'success',
                'pipeline_run_id': str(pipeline_run_id),
                'duration_seconds': duration,
                'extraction': extractions,
                'staging': staging_results,
                'transformation': transformation_results,
                'load': load_results,
            }
            
        except Exception as e:
            logger.error(f"[{pipeline_run_id}] Pipeline failed: {e}", exc_info=True)
            return {
                'status': 'error',
                'pipeline_run_id': str(pipeline_run_id),
                'error': str(e),
            }
    
    async def _extract_phase(self, pipeline_run_id: UUID) -> Dict:
        """Extract raw data from all sources concurrently"""
        
        results = {}
        
        # Run extractions in parallel
        tasks = {
            source: extractor.extract()
            for source, extractor in self.extractors.items()
        }
        
        extraction_results = await asyncio.gather(
            *tasks.values(),
            return_exceptions=True
        )
        
        for source, result in zip(tasks.keys(), extraction_results):
            if isinstance(result, Exception):
                logger.error(f"Extraction failed for {source}: {result}")
                results[source] = {'status': 'error', 'error': str(result)}
            else:
                results[source] = {
                    'status': 'success',
                    'records_extracted': len(result),
                    'sample': result[:1] if result else None,
                }
        
        return results
    
    async def _stage_phase(
        self, pipeline_run_id: UUID, extractions: Dict
    ) -> Dict:
        """Stage raw extracted data to staging tables"""
        
        results = {}
        
        for source in self.extractors.keys():
            if extractions[source]['status'] != 'success':
                results[source] = {'status': 'skipped', 'reason': 'extraction_failed'}
                continue
            
            try:
                # Get staging table class
                staging_table_name = f'{source}_staging'
                
                # Insert to staging (implementation depends on db library)
                inserted_count = await self.db.execute(
                    f"""INSERT INTO {staging_table_name} (...) 
                       VALUES (...) 
                       RETURNING COUNT(*)"""
                )
                
                results[source] = {
                    'status': 'success',
                    'records_staged': inserted_count,
                }
                
            except Exception as e:
                logger.error(f"Staging failed for {source}: {e}")
                results[source] = {'status': 'error', 'error': str(e)}
        
        return results
    
    async def _transform_phase(self, pipeline_run_id: UUID) -> Dict:
        """Transform staged data to canonical form"""
        
        results = {}
        
        for source, transformer in self.transformers.items():
            try:
                # Get staging data
                staging_table_name = f'{source}_staging'
                staging_rows = await self.db.fetch(
                    f"""SELECT * FROM {staging_table_name} 
                       WHERE extraction_id = :run_id
                       ORDER BY id""",
                    {'run_id': pipeline_run_id}
                )
                
                # Transform batch
                successes, failures = await transformer.process_staging_batch(
                    staging_rows
                )
                
                results[source] = {
                    'status': 'success' if not failures else 'partial',
                    'transformed_count': len(successes),
                    'failed_count': len(failures),
                    'failures': failures[:10],  # Sample
                }
                
            except Exception as e:
                logger.error(f"Transformation failed for {source}: {e}")
                results[source] = {'status': 'error', 'error': str(e)}
        
        return results
    
    async def _load_phase(
        self, pipeline_run_id: UUID, transformation_results: Dict
    ) -> Dict:
        """Load canonical data to database"""
        
        results = {}
        
        try:
            # Load in order: prospects first, then everything else
            async with self.db.transaction():
                # Load prospect_core
                prospects_loaded = await self._load_prospects(pipeline_run_id)
                
                # Load grades
                grades_loaded = await self._load_grades(pipeline_run_id)
                
                # Load college stats
                stats_loaded = await self._load_college_stats(pipeline_run_id)
                
                # Load measurements
                measurements_loaded = await self._load_measurements(pipeline_run_id)
                
                results = {
                    'status': 'success',
                    'prospects_loaded': prospects_loaded,
                    'grades_loaded': grades_loaded,
                    'stats_loaded': stats_loaded,
                    'measurements_loaded': measurements_loaded,
                }
                
        except Exception as e:
            logger.error(f"Load phase failed: {e}")
            results = {'status': 'error', 'error': str(e)}
        
        return results
    
    async def _publish_phase(self, pipeline_run_id: UUID):
        """Refresh materialized views and publish metrics"""
        
        # Refresh analytics views
        views_to_refresh = [
            'prospect_quality_scores',
            'position_benchmarks',
            'prospect_outliers',
        ]
        
        for view in views_to_refresh:
            await self.db.execute(f"REFRESH MATERIALIZED VIEW {view}")
        
        logger.info(f"[{pipeline_run_id}] Materialized views refreshed")
    
    async def _load_prospects(self, pipeline_run_id: UUID) -> int:
        """Load prospect_core records"""
        count = await self.db.execute(
            """INSERT INTO prospects 
               (name_first, name_last, position, college, pff_id, ...)
               SELECT name_first, name_last, position, college, pff_id, ...
               FROM prospect_core pc
               WHERE pc.extraction_id = :run_id
               ON CONFLICT (name_first, name_last, position, college)
               DO UPDATE SET updated_at = now()
               RETURNING COUNT(*)""",
            {'run_id': pipeline_run_id}
        )
        return count
    
    # Similar methods for _load_grades, _load_college_stats, etc.
```

---

## Monitoring & Observability

### Data Quality Scorecard

Create daily report showing data quality by source:

```sql
-- Dashboard query: Data Quality by Source
SELECT 
    source_system,
    COUNT(*) as records_processed,
    ROUND(100.0 * COUNT(CASE WHEN had_conflict THEN 1 END) / COUNT(*), 2) as conflict_pct,
    COUNT(DISTINCT entity_id) as unique_entities,
    AVG(EXTRACT(EPOCH FROM (changed_at - extraction_timestamp))) as avg_transform_seconds
FROM data_lineage
WHERE changed_at > now() - interval '1 day'
GROUP BY source_system
ORDER BY records_processed DESC;
```

### Prospect Data Lineage Query

Find complete history of specific prospect:

```sql
-- Show all transformations for a prospect
SELECT 
    field_name,
    value_previous,
    value_current,
    source_system,
    transformation_rule_id,
    changed_at,
    changed_by
FROM data_lineage
WHERE entity_id = :prospect_id
ORDER BY changed_at DESC;
```

---

## Deployment Checklist

- [ ] Create all staging tables (migration)
- [ ] Create canonical tables (migration)
- [ ] Create lineage table (migration)
- [ ] Implement base transformer framework
- [ ] Implement PFF transformer
- [ ] Implement CFR transformer
- [ ] Implement NFLCombine transformer
- [ ] Create ETL orchestrator
- [ ] Test end-to-end pipeline locally
- [ ] Deploy to staging environment
- [ ] Run full pipeline validation
- [ ] Deploy to production
- [ ] Monitor first 3 runs for issues
- [ ] Document transformation rules
- [ ] Create operational runbook
