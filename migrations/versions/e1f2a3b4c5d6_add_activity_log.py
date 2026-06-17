"""Add activity log (m10, RBAC + audit trail)

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-06-17 03:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'e1f2a3b4c5d6'
down_revision = 'd0e1f2a3b4c5'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'activity_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('username', sa.String(length=80), nullable=True),
        sa.Column('method', sa.String(length=10), nullable=True),
        sa.Column('endpoint', sa.String(length=120), nullable=True),
        sa.Column('path', sa.String(length=300), nullable=True),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_activity_log_created_at'), 'activity_log',
                    ['created_at'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_activity_log_created_at'), table_name='activity_log')
    op.drop_table('activity_log')
