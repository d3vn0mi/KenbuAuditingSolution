"""Add evidence repository: evidence, versions, link tables (m6)

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-06-17 01:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'a7b8c9d0e1f2'
down_revision = 'f6a7b8c9d0e1'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'evidence',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=300), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('evidence_type', sa.String(length=30), nullable=True),
        sa.Column('owner_id', sa.Integer(), nullable=True),
        sa.Column('valid_until', sa.Date(), nullable=True),
        sa.Column('review_date', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'evidence_versions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('evidence_id', sa.Integer(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('storage_name', sa.String(length=64), nullable=False),
        sa.Column('original_filename', sa.String(length=300), nullable=True),
        sa.Column('mime', sa.String(length=100), nullable=True),
        sa.Column('size', sa.Integer(), nullable=True),
        sa.Column('collected_at', sa.DateTime(), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['evidence_id'], ['evidence.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('evidence_id', 'version', name='uq_evidence_version'),
    )

    op.create_table(
        'evidence_controls',
        sa.Column('evidence_id', sa.Integer(), nullable=False),
        sa.Column('control_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['evidence_id'], ['evidence.id']),
        sa.ForeignKeyConstraint(['control_id'], ['controls.id']),
        sa.PrimaryKeyConstraint('evidence_id', 'control_id'),
    )

    op.create_table(
        'evidence_checks',
        sa.Column('evidence_id', sa.Integer(), nullable=False),
        sa.Column('check_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['evidence_id'], ['evidence.id']),
        sa.ForeignKeyConstraint(['check_id'], ['checks.id']),
        sa.PrimaryKeyConstraint('evidence_id', 'check_id'),
    )


def downgrade():
    op.drop_table('evidence_checks')
    op.drop_table('evidence_controls')
    op.drop_table('evidence_versions')
    op.drop_table('evidence')
