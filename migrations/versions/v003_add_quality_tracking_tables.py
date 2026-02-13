"""Add quality tracking tables for grade validation and alerting.

For US-044: Enhanced Data Quality for Multi-Source Grades

This migration creates:
- quality_rules: Configurable quality check rules per position/source
- quality_alerts: Alert history and audit trail with review workflow
- grade_history: Daily grade snapshots for trend analysis
- quality_metrics: Aggregated quality statistics for dashboard
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid


def upgrade():
    """Create quality tracking schema."""
    
    # Table 1: quality_rules - Configuration for quality checks per position/source
    op.create_table(
        'quality_rules',
        sa.Column('rule_id', postgresql.UUID(as_uuid=True), default=uuid.uuid4, nullable=False),
        sa.Column('rule_name', sa.String(255), nullable=False, unique=True),
        sa.Column('rule_type', sa.String(50), nullable=False),
        sa.Column('grade_source', sa.String(50), nullable=True),  # 'pff', 'espn', 'nfl', etc.
        sa.Column('position', sa.String(50), nullable=True),      # 'QB', 'EDGE', etc.
        sa.Column('threshold_type', sa.String(50), nullable=False),  # 'std_dev', 'percentage', etc.
        sa.Column('threshold_value', sa.Float(), nullable=False),
        sa.Column('severity', sa.String(50), nullable=False),
        sa.Column('enabled', sa.Boolean(), default=True, nullable=False),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('rule_id'),
        sa.UniqueConstraint('rule_name', 'position', 'grade_source', name='uq_rule_position_source'),
    )
    op.create_index('idx_rule_enabled_type', 'quality_rules', ['enabled', 'rule_type'])
    op.create_index('idx_rule_position_source', 'quality_rules', ['position', 'grade_source'])
    
    # Table 2: quality_alerts - Alert history and audit trail
    op.create_table(
        'quality_alerts',
        sa.Column('alert_id', postgresql.UUID(as_uuid=True), default=uuid.uuid4, nullable=False),
        sa.Column('prospect_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('rule_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('alert_type', sa.String(50), nullable=False),
        sa.Column('severity', sa.String(50), nullable=False),
        sa.Column('grade_source', sa.String(50), nullable=True),
        sa.Column('field_name', sa.String(255), nullable=True),
        sa.Column('field_value', sa.String(255), nullable=True),
        sa.Column('expected_value', sa.String(255), nullable=True),
        sa.Column('review_status', sa.String(50), default='pending', nullable=False),
        sa.Column('reviewed_by', sa.String(255), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('review_notes', sa.String(1000), nullable=True),
        sa.Column('escalated_at', sa.DateTime(), nullable=True),
        sa.Column('escalation_reason', sa.String(500), nullable=True),
        sa.Column('alert_metadata', sa.String(2000), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('alert_id'),
        sa.ForeignKeyConstraint(['prospect_id'], ['prospects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['rule_id'], ['quality_rules.rule_id'], ondelete='CASCADE'),
        sa.UniqueConstraint('prospect_id', 'rule_id', 'created_at', name='uq_alert_prospect_rule_time'),
    )
    op.create_index('idx_alert_prospect_created', 'quality_alerts', ['prospect_id', 'created_at'])
    op.create_index('idx_alert_severity', 'quality_alerts', ['severity'])
    op.create_index('idx_alert_review_status', 'quality_alerts', ['review_status'])
    op.create_index('idx_alert_grade_source', 'quality_alerts', ['grade_source'])
    op.create_index('idx_alert_created', 'quality_alerts', ['created_at'])
    
    # Table 3: grade_history - Daily snapshots for trend analysis
    op.create_table(
        'grade_history',
        sa.Column('history_id', postgresql.UUID(as_uuid=True), default=uuid.uuid4, nullable=False),
        sa.Column('prospect_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('grade_source', sa.String(50), nullable=False),
        sa.Column('grade_date', sa.DateTime(), nullable=False),
        sa.Column('grade_overall_raw', sa.Float(), nullable=False),
        sa.Column('grade_overall_normalized', sa.Float(), nullable=True),
        sa.Column('prior_grade', sa.Float(), nullable=True),
        sa.Column('grade_change', sa.Float(), nullable=True),
        sa.Column('change_percentage', sa.Float(), nullable=True),
        sa.Column('is_outlier', sa.Boolean(), default=False, nullable=False),
        sa.Column('outlier_type', sa.String(50), nullable=True),
        sa.Column('std_dev_from_mean', sa.Float(), nullable=True),
        sa.Column('position_mean', sa.Float(), nullable=True),
        sa.Column('position_stdev', sa.Float(), nullable=True),
        sa.Column('note', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('history_id'),
        sa.ForeignKeyConstraint(['prospect_id'], ['prospects.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('prospect_id', 'grade_source', 'grade_date', name='uq_grade_history_prospect_source_date'),
    )
    op.create_index('idx_grade_history_prospect_date', 'grade_history', ['prospect_id', 'grade_date'])
    op.create_index('idx_grade_history_source_date', 'grade_history', ['grade_source', 'grade_date'])
    op.create_index('idx_grade_history_outlier', 'grade_history', ['is_outlier'])
    op.create_index('idx_grade_history_created', 'grade_history', ['created_at'])
    
    # Table 4: quality_metrics - Aggregated statistics for dashboard
    op.create_table(
        'quality_metrics',
        sa.Column('metric_id', postgresql.UUID(as_uuid=True), default=uuid.uuid4, nullable=False),
        sa.Column('metric_date', sa.DateTime(), nullable=False),
        sa.Column('position', sa.String(50), nullable=True),
        sa.Column('grade_source', sa.String(50), nullable=True),
        sa.Column('total_prospects', sa.Integer(), default=0, nullable=False),
        sa.Column('prospects_with_grades', sa.Integer(), default=0, nullable=False),
        sa.Column('coverage_percentage', sa.Float(), nullable=False),
        sa.Column('total_grades_loaded', sa.Integer(), default=0, nullable=False),
        sa.Column('grades_validated', sa.Integer(), default=0, nullable=False),
        sa.Column('validation_percentage', sa.Float(), nullable=False),
        sa.Column('outliers_detected', sa.Integer(), default=0, nullable=False),
        sa.Column('outlier_percentage', sa.Float(), nullable=False),
        sa.Column('critical_outliers', sa.Integer(), default=0, nullable=False),
        sa.Column('alerts_generated', sa.Integer(), default=0, nullable=False),
        sa.Column('alerts_reviewed', sa.Integer(), default=0, nullable=False),
        sa.Column('alerts_escalated', sa.Integer(), default=0, nullable=False),
        sa.Column('quality_score', sa.Float(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('calculation_notes', sa.String(1000), nullable=True),
        sa.PrimaryKeyConstraint('metric_id'),
        sa.UniqueConstraint('metric_date', 'position', 'grade_source', name='uq_quality_metrics_date_position_source'),
    )
    op.create_index('idx_quality_metrics_date', 'quality_metrics', ['metric_date'])
    op.create_index('idx_quality_metrics_position_date', 'quality_metrics', ['position', 'metric_date'])


def downgrade():
    """Remove quality tracking schema."""
    
    # Drop tables in reverse order
    op.drop_table('quality_metrics')
    op.drop_table('grade_history')
    op.drop_table('quality_alerts')
    op.drop_table('quality_rules')
