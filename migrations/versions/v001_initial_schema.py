"""Create initial schema - V001

Revision ID: v001_initial_schema
Revises: 
Create Date: 2026-02-09 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'v001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial database schema."""
    
    # Create prospects table
    op.create_table(
        'prospects',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.func.gen_random_uuid()),
        sa.Column('name', sa.String(255), nullable=False, index=True),
        sa.Column('position', sa.String(10), nullable=False, index=True),
        sa.Column('college', sa.String(255), nullable=False, index=True),
        sa.Column('height', sa.Numeric(4, 2)),
        sa.Column('weight', sa.Integer()),
        sa.Column('arm_length', sa.Numeric(4, 2)),
        sa.Column('hand_size', sa.Numeric(4, 2)),
        sa.Column('draft_grade', sa.Numeric(3, 1)),
        sa.Column('round_projection', sa.Integer()),
        sa.Column('grade_source', sa.String(100)),
        sa.Column('status', sa.String(50), default='active', index=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now(), nullable=False, index=True),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', sa.String(100), default='system'),
        sa.Column('updated_by', sa.String(100), default='system'),
        sa.Column('data_source', sa.String(100), default='nfl.com'),
        sa.UniqueConstraint('name', 'position', 'college', name='idx_prospect_unique'),
        sa.CheckConstraint("position IN ('QB', 'RB', 'FB', 'WR', 'TE', 'OL', 'DL', 'EDGE', 'LB', 'DB', 'K', 'P')", name='ck_valid_position'),
        sa.CheckConstraint('height BETWEEN 5.5 AND 7.0', name='ck_valid_height'),
        sa.CheckConstraint('weight BETWEEN 150 AND 350', name='ck_valid_weight'),
        sa.CheckConstraint('draft_grade BETWEEN 5.0 AND 10.0', name='ck_valid_draft_grade'),
    )
    
    # Create other tables as defined in models.py
    # This is simplified - in production, use alembic autogenerate


def downgrade() -> None:
    """Drop initial database schema."""
    op.drop_table('prospects')
