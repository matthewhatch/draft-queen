"""ETL Architecture - Create Staging Tables (V004)

Revision ID: v004_etl_staging_tables
Revises: v003_add_quality_tracking_tables
Create Date: 2026-02-15 10:00:00.000000

This migration implements the ETL foundation layer with source-specific
staging tables for capturing raw, unmodified data from external sources.

Tables created:
- pff_staging: PFF grades (0-100 scale, unmodified)
- nfl_combine_staging: NFL combine test results
- cfr_staging: College Football Reference statistics
- yahoo_staging: Yahoo draft projections
- espn_staging: ESPN injury reports (schema only, Phase 2)

Each staging table:
- Is immutable (never updated, only truncated and reloaded)
- Captures raw data exactly as received from source
- Tracks extraction metadata (extraction_id, timestamp, hash)
- Includes indexes for efficient transformation queries
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'v004_etl_staging_tables'
down_revision = 'v003_add_quality_tracking_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create ETL staging tables."""

    # ========== PFF STAGING TABLE ==========
    # Captures raw PFF grades and evaluations
    op.create_table(
        'pff_staging',
        sa.Column('id', sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column('extraction_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        
        # Prospect Identity (from PFF)
        sa.Column('pff_id', sa.String(50), nullable=False),
        sa.Column('first_name', sa.String(255)),
        sa.Column('last_name', sa.String(255)),
        sa.Column('position', sa.String(10)),
        sa.Column('college', sa.String(255)),
        sa.Column('draft_year', sa.Integer),
        
        # PFF Proprietary Grades (0-100 scale, raw)
        sa.Column('overall_grade', sa.Numeric(5, 2)),
        sa.Column('position_grade', sa.Numeric(5, 2)),
        sa.Column('trade_grade', sa.Numeric(5, 2)),
        sa.Column('scheme_fit_grade', sa.Numeric(5, 2)),
        
        # Physical Attributes (from PFF, unverified)
        sa.Column('height_inches', sa.Integer),
        sa.Column('weight_lbs', sa.Integer),
        sa.Column('arm_length_inches', sa.Numeric(3, 1)),
        sa.Column('hand_size_inches', sa.Numeric(3, 2)),
        
        # Metadata
        sa.Column('film_watched_snaps', sa.Integer),
        sa.Column('games_analyzed', sa.Integer),
        sa.Column('grade_issued_date', sa.Date),
        sa.Column('grade_is_preliminary', sa.Boolean()),
        
        # Lineage & Quality
        sa.Column('raw_json_data', postgresql.JSONB()),
        sa.Column('data_hash', sa.String(64)),
        sa.Column('extraction_timestamp', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('extraction_status', sa.String(50)),  # success, partial, error
        sa.Column('notes', sa.Text),
        
        # Constraints
        sa.UniqueConstraint('pff_id', 'extraction_id', name='uq_pff_staging_extraction'),
        sa.Index('idx_pff_staging_extraction_id', 'extraction_id'),
        sa.Index('idx_pff_staging_draft_year', 'draft_year'),
        sa.Index('idx_pff_staging_position', 'position'),
    )

    # ========== NFL COMBINE STAGING TABLE ==========
    # Captures raw NFL combine test results
    op.create_table(
        'nfl_combine_staging',
        sa.Column('id', sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column('extraction_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        
        # Prospect Identity (from NFL)
        sa.Column('nfl_combine_id', sa.String(50)),
        sa.Column('first_name', sa.String(255)),
        sa.Column('last_name', sa.String(255)),
        sa.Column('position', sa.String(10)),
        sa.Column('college', sa.String(255)),
        
        # Test Metadata
        sa.Column('test_date', sa.Date),
        sa.Column('location', sa.String(100)),  # Indianapolis, pro day, etc.
        sa.Column('test_type', sa.String(50)),  # combine, pro_day, private
        
        # Raw Test Results (exactly as recorded, no parsing)
        sa.Column('height_feet_inches', sa.String(10)),  # "6-2" format
        sa.Column('weight_lbs', sa.Numeric(5, 1)),
        sa.Column('forty_yard_dash', sa.Numeric(4, 3)),
        sa.Column('ten_yard_split', sa.Numeric(4, 3)),
        sa.Column('twenty_yard_split', sa.Numeric(4, 3)),
        sa.Column('bench_press_reps', sa.Integer),
        sa.Column('vertical_jump_inches', sa.Numeric(5, 2)),
        sa.Column('broad_jump_inches', sa.Numeric(5, 2)),
        sa.Column('shuttle_run', sa.Numeric(4, 3)),
        sa.Column('three_cone_drill', sa.Numeric(4, 3)),
        sa.Column('sixty_yard_shuttle', sa.Numeric(4, 3)),
        
        # Position-Specific Tests
        sa.Column('wonderlic_score', sa.Integer),  # QB cognition
        sa.Column('arm_length_inches', sa.Numeric(3, 1)),
        sa.Column('hand_size_inches', sa.Numeric(3, 2)),
        
        # Lineage & Quality
        sa.Column('raw_json_data', postgresql.JSONB()),
        sa.Column('data_hash', sa.String(64)),
        sa.Column('extraction_timestamp', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('test_invalidated', sa.Boolean()),  # Marked by NFL as invalid
        
        # Constraints
        sa.UniqueConstraint('nfl_combine_id', 'test_date', 'test_type', 
                           name='uq_nfl_combine_staging_test'),
        sa.Index('idx_nfl_combine_staging_extraction_id', 'extraction_id'),
        sa.Index('idx_nfl_combine_staging_test_date', 'test_date'),
        sa.Index('idx_nfl_combine_staging_position', 'position'),
    )

    # ========== CFR STAGING TABLE ==========
    # Captures raw College Football Reference statistics
    op.create_table(
        'cfr_staging',
        sa.Column('id', sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column('extraction_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        
        # Prospect Identity (from CFR)
        sa.Column('cfr_player_id', sa.String(100)),
        sa.Column('cfr_player_url', sa.String(500)),
        sa.Column('first_name', sa.String(255)),
        sa.Column('last_name', sa.String(255)),
        
        # College & Context
        sa.Column('college', sa.String(255)),
        sa.Column('position', sa.String(10)),
        sa.Column('recruit_year', sa.Integer),
        sa.Column('class_year', sa.String(20)),  # "2026", "Junior", "Senior"
        
        # Season & Participation
        sa.Column('season', sa.Integer, nullable=False),
        sa.Column('games_played', sa.Integer),
        sa.Column('games_started', sa.Integer),
        
        # Offensive Stats (All Positions)
        sa.Column('passing_attempts', sa.Integer),
        sa.Column('passing_completions', sa.Integer),
        sa.Column('passing_yards', sa.Integer),
        sa.Column('passing_touchdowns', sa.Integer),
        sa.Column('passing_interceptions', sa.Integer),
        sa.Column('completion_percentage', sa.Numeric(5, 2)),
        sa.Column('qb_rating', sa.Numeric(5, 2)),
        
        sa.Column('rushing_attempts', sa.Integer),
        sa.Column('rushing_yards', sa.Integer),
        sa.Column('rushing_yards_per_attempt', sa.Numeric(5, 2)),
        sa.Column('rushing_touchdowns', sa.Integer),
        
        sa.Column('receiving_targets', sa.Integer),
        sa.Column('receiving_receptions', sa.Integer),
        sa.Column('receiving_yards', sa.Integer),
        sa.Column('receiving_yards_per_reception', sa.Numeric(5, 2)),
        sa.Column('receiving_touchdowns', sa.Integer),
        
        # Defensive Stats
        sa.Column('tackles', sa.Integer),
        sa.Column('assisted_tackles', sa.Integer),
        sa.Column('tackles_for_loss', sa.Numeric(5, 1)),
        sa.Column('sacks', sa.Numeric(5, 1)),
        sa.Column('forced_fumbles', sa.Integer),
        sa.Column('fumble_recoveries', sa.Integer),
        sa.Column('passes_defended', sa.Integer),
        sa.Column('interceptions_defensive', sa.Integer),
        
        # Offensive Line
        sa.Column('linemen_games_started', sa.Integer),
        sa.Column('all_conference_selections', sa.Integer),
        
        # Lineage & Quality
        sa.Column('raw_html_hash', sa.String(64)),
        sa.Column('data_hash', sa.String(64)),
        sa.Column('extraction_timestamp', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('parsing_confidence', sa.Numeric(3, 2)),  # 0-1.0
        
        # Constraints
        sa.UniqueConstraint('cfr_player_id', 'season', name='uq_cfr_staging_season'),
        sa.Index('idx_cfr_staging_extraction_id', 'extraction_id'),
        sa.Index('idx_cfr_staging_college_season', 'college', 'season'),
        sa.Index('idx_cfr_staging_position', 'position'),
    )

    # ========== YAHOO STAGING TABLE ==========
    # Captures raw Yahoo Sports draft projections
    op.create_table(
        'yahoo_staging',
        sa.Column('id', sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column('extraction_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        
        # Prospect Identity
        sa.Column('yahoo_id', sa.String(50)),
        sa.Column('first_name', sa.String(255)),
        sa.Column('last_name', sa.String(255)),
        sa.Column('position', sa.String(10)),
        sa.Column('college', sa.String(255)),
        
        # Rankings & Projections
        sa.Column('overall_rank', sa.Integer),
        sa.Column('position_rank', sa.Integer),
        sa.Column('round_projection', sa.Integer),
        sa.Column('team_projection', sa.String(100)),  # Projected team
        
        # Analysis
        sa.Column('yahoo_grade', sa.Numeric(3, 1)),  # 5.0-10.0 scale
        sa.Column('strengths', sa.Text),
        sa.Column('weaknesses', sa.Text),
        sa.Column('comps', sa.String(255)),  # Comparable player
        sa.Column('analyst_name', sa.String(255)),
        sa.Column('analysis_date', sa.Date),
        
        # Lineage & Quality
        sa.Column('article_url', sa.String(500)),
        sa.Column('raw_json_data', postgresql.JSONB()),
        sa.Column('data_hash', sa.String(64)),
        sa.Column('extraction_timestamp', sa.DateTime(), server_default=sa.func.now()),
        
        # Constraints
        sa.UniqueConstraint('yahoo_id', 'extraction_id', name='uq_yahoo_staging_extraction'),
        sa.Index('idx_yahoo_staging_extraction_id', 'extraction_id'),
        sa.Index('idx_yahoo_staging_position', 'position'),
    )

    # ========== ESPN STAGING TABLE ==========
    # Captures raw ESPN injury reports and updates
    op.create_table(
        'espn_staging',
        sa.Column('id', sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column('extraction_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        
        # Prospect Identity
        sa.Column('espn_id', sa.String(50)),
        sa.Column('first_name', sa.String(255)),
        sa.Column('last_name', sa.String(255)),
        sa.Column('position', sa.String(10)),
        sa.Column('college', sa.String(255)),
        
        # Injury Information
        sa.Column('injury_status', sa.String(50)),  # questionable, doubtful, out
        sa.Column('injury_description', sa.Text),
        sa.Column('injury_date', sa.Date),
        sa.Column('return_expected_date', sa.Date),
        sa.Column('impact_assessment', sa.String(100)),  # high, medium, low
        
        # Report Metadata
        sa.Column('report_date', sa.Date),
        sa.Column('reporter_name', sa.String(255)),
        sa.Column('article_url', sa.String(500)),
        
        # Lineage & Quality
        sa.Column('raw_json_data', postgresql.JSONB()),
        sa.Column('data_hash', sa.String(64)),
        sa.Column('extraction_timestamp', sa.DateTime(), server_default=sa.func.now()),
        
        # Constraints
        sa.Index('idx_espn_staging_extraction_id', 'extraction_id'),
        sa.Index('idx_espn_staging_position', 'position'),
    )

    # ========== PIPELINE RUNS METADATA TABLE ==========
    # Tracks metadata for each ETL pipeline execution
    op.create_table(
        'etl_pipeline_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.func.gen_random_uuid()),
        sa.Column('extraction_id', postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        
        # Execution Timing
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime()),
        sa.Column('duration_seconds', sa.Integer),
        
        # Phases Completed
        sa.Column('extract_phase_status', sa.String(50)),  # success, partial, error
        sa.Column('stage_phase_status', sa.String(50)),
        sa.Column('validate_phase_status', sa.String(50)),
        sa.Column('transform_phase_status', sa.String(50)),
        sa.Column('load_phase_status', sa.String(50)),
        sa.Column('publish_phase_status', sa.String(50)),
        
        # Source Status
        sa.Column('source_status', postgresql.JSONB()),  # {pff: success, nfl: partial, ...}
        
        # Quality Metrics
        sa.Column('total_staged_records', sa.Integer),
        sa.Column('total_validated_records', sa.Integer),
        sa.Column('total_transformed_records', sa.Integer),
        sa.Column('error_count', sa.Integer, default=0),
        sa.Column('warning_count', sa.Integer, default=0),
        
        # Logs
        sa.Column('execution_log', sa.Text),
        sa.Column('error_log', sa.Text),
        
        # Audit
        sa.Column('triggered_by', sa.String(100), default='scheduler'),  # scheduler, manual, api
        sa.Column('triggered_by_user', sa.String(255)),
        sa.Column('notes', sa.Text),
        
        sa.Index('idx_etl_pipeline_runs_started_at', 'started_at'),
    )


def downgrade() -> None:
    """Drop ETL staging tables."""
    op.drop_table('etl_pipeline_runs')
    op.drop_table('espn_staging')
    op.drop_table('yahoo_staging')
    op.drop_table('cfr_staging')
    op.drop_table('nfl_combine_staging')
    op.drop_table('pff_staging')
