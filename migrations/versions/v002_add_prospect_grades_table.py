"""Add prospect_grades table - V002

Revision ID: v002_add_prospect_grades_table
Revises: v001_initial_schema
Create Date: 2026-02-12 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'v002_add_prospect_grades_table'
down_revision = 'v001_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create prospect_grades table."""
    
    op.create_table(
        'prospect_grades',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('prospect_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source', sa.String(50), nullable=False),
        sa.Column('grade_overall', sa.Float(), nullable=True),
        sa.Column('grade_normalized', sa.Float(), nullable=True),
        sa.Column('grade_position', sa.String(10), nullable=True),
        sa.Column('match_confidence', sa.Float(), nullable=True),
        sa.Column('grade_date', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', sa.String(50), nullable=True, server_default='pff_loader'),
        
        sa.ForeignKeyConstraint(['prospect_id'], ['prospects.id'], name='fk_prospect_grades_prospect_id', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('prospect_id', 'source', 'grade_date', name='uq_prospect_grade_source_date'),
        sa.Index('idx_grade_source', 'source'),
        sa.Index('idx_grade_prospect', 'prospect_id'),
    )


def downgrade() -> None:
    """Drop prospect_grades table."""
    op.drop_table('prospect_grades')
