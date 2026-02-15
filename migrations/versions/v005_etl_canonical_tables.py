"""ETL Architecture - Create Canonical Tables (V005)

Revision ID: v005_etl_canonical_tables
Revises: v004_etl_staging_tables
Create Date: 2026-02-15 11:00:00.000000

This migration creates the canonical (transformed) layer - the single source of truth
for all prospect data. These tables are where raw staging data is normalized, deduplicated,
and merged into business entities.

Tables created:
- prospect_core: Identity hub (deduplication across all sources)
- prospect_grades: Multi-source normalized grades (5.0-10.0 scale)
- prospect_measurements: Reconciled physical measurements (conflict resolution)
- prospect_college_stats: Position-normalized college statistics
- data_lineage: Complete audit trail (source → transform → field value)

Design principles:
- prospect_core is the identity hub (single prospect record)
- All other canonical tables reference prospect_core.id
- data_lineage tracks every field change with source attribution
- Immutable history: all changes recorded, never updated/deleted
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'v005_etl_canonical_tables'
down_revision = 'v004_etl_staging_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create ETL canonical (transformed) tables."""

    # Drop existing tables that will be replaced with new schema
    # (These were created by earlier migrations)
    op.execute("DROP TABLE IF EXISTS prospect_grades CASCADE")
    op.execute("DROP TABLE IF EXISTS prospect_core CASCADE")
    op.execute("DROP TABLE IF EXISTS data_lineage CASCADE")
    op.execute("DROP TABLE IF EXISTS prospect_college_stats CASCADE")
    op.execute("DROP TABLE IF EXISTS prospect_measurements CASCADE")

    # ========== PROSPECT CORE (Identity Hub) ==========
    # Single source of truth for prospect identity
    # Deduplication keys link to all external sources
    op.create_table(
        'prospect_core',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.func.gen_random_uuid()),
        
        # Primary Identity (Canonical)
        sa.Column('name_first', sa.String(255), nullable=False, index=True),
        sa.Column('name_last', sa.String(255), nullable=False, index=True),
        sa.Column('position', sa.String(10), nullable=False, index=True),
        sa.Column('college', sa.String(255), nullable=False, index=True),
        sa.Column('recruit_year', sa.Integer),
        
        # Source Identifiers (Deduplication Keys)
        # These link back to source systems for record matching
        sa.Column('pff_id', sa.String(50), unique=True, index=True),
        sa.Column('nfl_combine_id', sa.String(50), index=True),
        sa.Column('cfr_player_id', sa.String(100), index=True),
        sa.Column('yahoo_id', sa.String(50), index=True),
        sa.Column('espn_id', sa.String(50), index=True),
        
        # Master Status & Quality
        sa.Column('status', sa.String(50), default='active', index=True),  # active, withdrawn, injury, undecided
        sa.Column('is_international', sa.Boolean(), default=False),
        sa.Column('data_quality_score', sa.Numeric(3, 2)),  # 0-1.0, based on source coverage
        
        # Source of Truth Attribution
        sa.Column('created_from_source', sa.String(100)),  # Which source created this record
        sa.Column('primary_source', sa.String(100)),  # Current primary source for matching
        
        # Audit & Timestamps
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), index=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('last_extraction_id', postgresql.UUID(as_uuid=True)),  # Last ETL run that touched this
        
        # Constraints: Identity is unique across name + position + college
        sa.UniqueConstraint('name_first', 'name_last', 'position', 'college', 
                           name='uq_prospect_identity'),
        
        # Indexes for query performance
        sa.Index('idx_prospect_core_status', 'status'),
        sa.Index('idx_prospect_core_quality', 'data_quality_score'),
        sa.Index('idx_prospect_core_position_college', 'position', 'college'),
    )

    # ========== PROSPECT GRADES (Multi-Source Normalization) ==========
    # Stores grades from all sources, normalized to 5.0-10.0 scale
    # Multiple grades per prospect (one per source)
    op.create_table(
        'prospect_grades',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.func.gen_random_uuid()),
        sa.Column('prospect_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        
        # Source Information
        sa.Column('source', sa.String(100), nullable=False),  # pff, yahoo, espn, nfl
        sa.Column('source_system_id', sa.String(100)),  # ID in source system
        
        # Raw Grade (As Reported)
        sa.Column('grade_raw', sa.Numeric(5, 2)),  # Original value from source
        sa.Column('grade_raw_scale', sa.String(20)),  # Scale it was on (0-100, 5.0-10.0, etc.)
        
        # Normalized Grade (Standardized to 5.0-10.0)
        sa.Column('grade_normalized', sa.Numeric(3, 1), index=True),  # Our standard scale
        sa.Column('grade_normalized_method', sa.String(100)),  # Curve applied (linear, log, etc.)
        
        # Position-Specific Grades
        sa.Column('position_rated', sa.String(10)),  # Position at time of grading
        sa.Column('position_grade', sa.Numeric(5, 2)),  # Position-specific grade if provided
        
        # Confidence & Metadata
        sa.Column('sample_size', sa.Integer),  # Snaps analyzed, games watched, etc.
        sa.Column('grade_issued_date', sa.Date),
        sa.Column('grade_is_preliminary', sa.Boolean()),  # In-season: may change
        sa.Column('analyst_name', sa.String(255)),
        sa.Column('analyst_tier', sa.String(50)),  # expert, analyst, consensus
        
        # Lineage
        sa.Column('staged_from_id', sa.BigInteger()),  # Reference to staging table row
        sa.Column('transformation_rules', postgresql.JSONB()),  # Rules applied
        sa.Column('data_confidence', sa.Numeric(3, 2)),  # 0-1.0, how sure are we about this?
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        
        # Constraints
        sa.ForeignKeyConstraint(['prospect_id'], ['prospect_core.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('prospect_id', 'source', 'grade_issued_date', 
                           name='uq_prospect_grades_source_date'),
        
        # Indexes
        sa.Index('idx_prospect_grades_source', 'source'),
        sa.Index('idx_prospect_grades_prospect_source', 'prospect_id', 'source'),
    )

    # ========== PROSPECT MEASUREMENTS (Multi-Source Resolution) ==========
    # Physical measurements with conflict resolution
    # Height from NFL, weight from PFF, etc. - tracks source per field
    op.create_table(
        'prospect_measurements',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.func.gen_random_uuid()),
        sa.Column('prospect_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        
        # Physical Attributes (Reported)
        sa.Column('height_inches', sa.Numeric(3, 1)),  # Resolved height
        sa.Column('weight_lbs', sa.Numeric(5, 1)),  # Resolved weight
        sa.Column('arm_length_inches', sa.Numeric(3, 1)),
        sa.Column('hand_size_inches', sa.Numeric(3, 2)),
        
        # Test Results (Combine/Pro Day)
        sa.Column('forty_yard_dash', sa.Numeric(4, 3)),
        sa.Column('ten_yard_split', sa.Numeric(4, 3)),
        sa.Column('twenty_yard_split', sa.Numeric(4, 3)),
        sa.Column('bench_press_reps', sa.Integer),
        sa.Column('vertical_jump_inches', sa.Numeric(5, 2)),
        sa.Column('broad_jump_inches', sa.Numeric(5, 2)),
        sa.Column('shuttle_run', sa.Numeric(4, 3)),
        sa.Column('three_cone_drill', sa.Numeric(4, 3)),
        sa.Column('sixty_yard_shuttle', sa.Numeric(4, 3)),
        
        # Test Context
        sa.Column('test_date', sa.Date),
        sa.Column('test_type', sa.String(50)),  # combine, pro_day, private
        sa.Column('location', sa.String(100)),
        sa.Column('test_invalidated', sa.Boolean()),  # Flag: ignore this test
        
        # Source Attribution (Per Field)
        sa.Column('sources', postgresql.JSONB()),  # {height: nfl_combine, weight: pff, ...}
        sa.Column('source_conflicts', postgresql.JSONB()),  # {weight: [{source: nfl, value: 310}, ...]}
        sa.Column('resolved_by', sa.String(100)),  # official_combine, most_recent, manual_review, priority_order
        
        # Data Quality
        sa.Column('measurement_confidence', sa.Numeric(3, 2)),  # 0-1.0
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        
        # Constraints
        sa.ForeignKeyConstraint(['prospect_id'], ['prospect_core.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('prospect_id', 'test_date', 'test_type', 
                           name='uq_prospect_measurements_test'),
        
        # Indexes
        sa.Index('idx_prospect_measurements_prospect_id', 'prospect_id'),
        sa.Index('idx_prospect_measurements_test_date', 'test_date'),
    )

    # ========== PROSPECT COLLEGE STATS (Position-Normalized) ==========
    # College statistics with position-specific normalization
    op.create_table(
        'prospect_college_stats',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.func.gen_random_uuid()),
        sa.Column('prospect_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        
        # Season & Context
        sa.Column('season', sa.Integer, nullable=False),
        sa.Column('college', sa.String(255), nullable=False),
        sa.Column('class_year', sa.String(20)),  # Junior, Senior, etc.
        
        # Participation
        sa.Column('games_played', sa.Integer),
        sa.Column('games_started', sa.Integer),
        sa.Column('snaps_played', sa.Integer),
        
        # Shared Offensive Stats
        sa.Column('total_touches', sa.Integer),
        sa.Column('total_yards', sa.Integer),
        sa.Column('total_yards_per_touch', sa.Numeric(5, 2)),
        sa.Column('total_touchdowns', sa.Integer),
        
        # QB-Specific Stats (NULL for non-QBs)
        sa.Column('passing_attempts', sa.Integer),
        sa.Column('passing_completions', sa.Integer),
        sa.Column('passing_yards', sa.Integer),
        sa.Column('passing_touchdowns', sa.Integer),
        sa.Column('interceptions_thrown', sa.Integer),
        sa.Column('completion_percentage', sa.Numeric(5, 2)),
        sa.Column('qb_rating', sa.Numeric(5, 2)),
        
        # Rushing Stats (RB/WR/QB/TE)
        sa.Column('rushing_attempts', sa.Integer),
        sa.Column('rushing_yards', sa.Integer),
        sa.Column('rushing_yards_per_attempt', sa.Numeric(5, 2)),
        sa.Column('rushing_touchdowns', sa.Integer),
        
        # Receiving Stats (WR/TE/RB/QB)
        sa.Column('receiving_targets', sa.Integer),
        sa.Column('receiving_receptions', sa.Integer),
        sa.Column('receiving_yards', sa.Integer),
        sa.Column('receiving_yards_per_reception', sa.Numeric(5, 2)),
        sa.Column('receiving_touchdowns', sa.Integer),
        
        # Defense Stats
        sa.Column('tackles_solo', sa.Integer),
        sa.Column('tackles_assisted', sa.Integer),
        sa.Column('tackles_total', sa.Numeric(5, 1)),
        sa.Column('tackles_for_loss', sa.Numeric(5, 1)),
        sa.Column('sacks', sa.Numeric(5, 1)),
        sa.Column('forced_fumbles', sa.Integer),
        sa.Column('fumble_recoveries', sa.Integer),
        sa.Column('passes_defended', sa.Integer),
        sa.Column('interceptions_defensive', sa.Integer),
        
        # Offensive Line Specific
        sa.Column('games_started_ol', sa.Integer),
        sa.Column('all_conference_selections', sa.Integer),
        
        # Derived Metrics
        sa.Column('efficiency_rating', sa.Numeric(5, 2)),  # Position-specific
        sa.Column('statistical_percentile', sa.Numeric(5, 2)),  # vs position peers
        sa.Column('production_tier', sa.String(50)),  # elite, high, average, low
        
        # Lineage & Quality
        sa.Column('data_sources', postgresql.JSONB()),  # ['cfr', 'espn_box_score', ...]
        sa.Column('staged_from_id', sa.BigInteger()),
        sa.Column('transformation_timestamp', sa.DateTime()),
        sa.Column('data_completeness', sa.Numeric(3, 2)),  # 0-1.0, % of expected fields
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        
        # Constraints
        sa.ForeignKeyConstraint(['prospect_id'], ['prospect_core.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('prospect_id', 'season', name='uq_prospect_college_stats_season'),
        
        # Indexes
        sa.Index('idx_prospect_college_stats_prospect_season', 'prospect_id', 'season'),
        sa.Index('idx_prospect_college_stats_season', 'season'),
        sa.Index('idx_prospect_college_stats_college_season', 'college', 'season'),
        sa.Index('idx_prospect_college_stats_percentile', 'statistical_percentile'),
    )

    # ========== DATA LINEAGE (Audit Trail) ==========
    # Complete history of every field transformation
    # Answers: "Where did this value come from? What changed it?"
    op.create_table(
        'data_lineage',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.func.gen_random_uuid()),
        
        # Entity Being Tracked
        sa.Column('entity_type', sa.String(50), nullable=False),  # prospect_core, prospect_grades, etc.
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('field_name', sa.String(100), nullable=False),  # e.g., height_inches, grade_normalized
        
        # Value History
        sa.Column('value_current', sa.Text),  # New value
        sa.Column('value_previous', sa.Text),  # Old value
        sa.Column('value_is_null', sa.Boolean()),  # Was it NULL?
        
        # Source & Pipeline
        sa.Column('extraction_id', postgresql.UUID(as_uuid=True), index=True),  # Which ETL run
        sa.Column('source_table', sa.String(100)),  # pff_staging, nfl_combine_staging, etc.
        sa.Column('source_row_id', sa.BigInteger()),  # Row ID in staging table
        sa.Column('source_system', sa.String(50), index=True),  # pff, nfl_combine, cfr, yahoo, espn
        
        # Transformation Applied
        sa.Column('transformation_rule_id', sa.String(100)),  # e.g., pff_grade_normalization_curve
        sa.Column('transformation_logic', sa.Text),  # SQL/python code applied
        sa.Column('transformation_is_automated', sa.Boolean(), default=True),
        
        # Conflict Resolution
        sa.Column('had_conflict', sa.Boolean(), default=False),  # Multiple sources provided values
        sa.Column('conflicting_sources', postgresql.JSONB()),  # {pff: 87.5, yahoo: 82.0, ...}
        sa.Column('conflict_resolution_rule', sa.String(100)),  # priority_order, most_recent, etc.
        
        # Audit & Accountability
        sa.Column('changed_at', sa.DateTime(), server_default=sa.func.now(), index=True),
        sa.Column('changed_by', sa.String(100), default='system'),  # User or 'system'
        sa.Column('change_reason', sa.Text),  # Manual override reason
        sa.Column('change_reviewed_by', sa.String(100)),  # Who reviewed this change
        
        # Constraints & Indexes
        sa.Index('idx_lineage_entity', 'entity_type', 'entity_id'),
        sa.Index('idx_lineage_entity_field', 'entity_type', 'entity_id', 'field_name'),
        sa.Index('idx_lineage_source_system', 'source_system'),
        sa.Index('idx_lineage_extraction_id', 'extraction_id'),
        sa.Index('idx_lineage_changed_at', 'changed_at'),
    )

    # ========== MATERIALIZED VIEW: Prospect Summary ==========
    # Fast query combining canonical + lineage data
    op.execute("""
        CREATE MATERIALIZED VIEW vw_prospect_summary AS
        SELECT
            pc.id,
            pc.name_first,
            pc.name_last,
            pc.position,
            pc.college,
            pc.recruit_year,
            pc.pff_id,
            pc.nfl_combine_id,
            pc.cfr_player_id,
            pc.yahoo_id,
            pc.status,
            pc.data_quality_score,
            pc.created_at,
            pc.updated_at,
            -- Grade summary (PFF is primary)
            (SELECT grade_normalized FROM prospect_grades 
             WHERE prospect_id = pc.id AND source = 'pff' 
             ORDER BY grade_issued_date DESC LIMIT 1) as pff_grade_latest,
            -- Measurement summary
            pm.height_inches,
            pm.weight_lbs,
            pm.forty_yard_dash,
            -- College stats (latest season)
            (SELECT total_yards FROM prospect_college_stats 
             WHERE prospect_id = pc.id 
             ORDER BY season DESC LIMIT 1) as college_total_yards_latest
        FROM prospect_core pc
        LEFT JOIN prospect_measurements pm ON pc.id = pm.prospect_id
        WHERE pc.status = 'active';
    """)


def downgrade() -> None:
    """Drop ETL canonical tables and views."""
    op.execute("DROP MATERIALIZED VIEW IF EXISTS vw_prospect_summary")
    op.drop_table('data_lineage')
    op.drop_table('prospect_college_stats')
    op.drop_table('prospect_measurements')
    op.drop_table('prospect_grades')
    op.drop_table('prospect_core')
