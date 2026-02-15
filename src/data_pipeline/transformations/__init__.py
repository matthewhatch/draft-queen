"""ETL Transformation Framework

This module provides the base classes and utilities for transforming raw staging data
into canonical business entities.

Main components:
- BaseTransformer: Abstract base class for all transformers
- TransformationResult: Result object containing field changes and lineage
- LineageRecorder: Utility for recording complete audit trail
- FieldChange: Individual field transformation record

Usage:
    from data_pipeline.transformations.base_transformer import BaseTransformer
    from data_pipeline.transformations.lineage_recorder import LineageRecorder
    
    class MyTransformer(BaseTransformer):
        SOURCE_NAME = 'my_source'
        STAGING_TABLE_NAME = 'my_staging'
        
        async def validate_staging_data(self, row): ...
        async def get_prospect_identity(self, row): ...
        async def transform_staging_to_canonical(self, row, prospect_id): ...
        async def _match_or_create_prospect(self, identity, row): ...
    
    transformer = MyTransformer(db_session, extraction_id)
    results, failures = await transformer.process_staging_batch(staging_rows)

Pattern:
    1. Validate: Check that staging data is complete and valid
    2. Match: Extract prospect identity and match to existing prospect_core
    3. Normalize: Convert raw values to canonical form (e.g., 0-100 → 5.0-10.0)
    4. Reconcile: Handle conflicts (multiple sources, different values)
    5. Load: Insert transformed data and record lineage
    6. Publish: Update materialized views and analytics

See documentation in docs/architecture/ETL-IMPLEMENTATION-GUIDE.md for complete guide.
"""

from .base_transformer import (
    BaseTransformer,
    TransformationResult,
    FieldChange,
    TransformationPhase,
    ValidationError,
)
from .lineage_recorder import LineageRecorder

__all__ = [
    'BaseTransformer',
    'TransformationResult',
    'FieldChange',
    'TransformationPhase',
    'ValidationError',
    'LineageRecorder',
]
