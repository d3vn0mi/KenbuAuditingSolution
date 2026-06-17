"""Add findings + finding->control linkage (m7)

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-06-17 02:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'b8c9d0e1f2a3'
down_revision = 'a7b8c9d0e1f2'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'findings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=300), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('source', sa.String(length=20), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('remediation', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('discovered_at', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('promoted_from_pentest_finding_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['promoted_from_pentest_finding_id'], ['pentest_findings.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'finding_controls',
        sa.Column('finding_id', sa.Integer(), nullable=False),
        sa.Column('control_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['finding_id'], ['findings.id']),
        sa.ForeignKeyConstraint(['control_id'], ['controls.id']),
        sa.PrimaryKeyConstraint('finding_id', 'control_id'),
    )


def downgrade():
    op.drop_table('finding_controls')
    op.drop_table('findings')
