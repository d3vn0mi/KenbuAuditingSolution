"""Add the Control hub: obligations, controls, mappings (regulatory layer m2)

Creates the rich regulatory layer alongside the technical-check model:
obligations (hierarchical, per regulation), controls (cross-framework hub),
evidence requirements, external references, and the control<->obligation /
control<->check mapping tables. All new tables; no changes to existing schema.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-06-17 00:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e5f6a7b8c9d0'
down_revision = 'd4e5f6a7b8c9'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'obligations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('regulation_id', sa.Integer(), nullable=False),
        sa.Column('parent_id', sa.Integer(), nullable=True),
        sa.Column('ref', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=300), nullable=False),
        sa.Column('text', sa.Text(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=True),
        sa.Column('content_hash', sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(['regulation_id'], ['regulations.id']),
        sa.ForeignKeyConstraint(['parent_id'], ['obligations.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('regulation_id', 'ref', name='uq_obligation_regulation_ref'),
    )

    op.create_table(
        'controls',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=30), nullable=False),
        sa.Column('title', sa.String(length=300), nullable=False),
        sa.Column('domain', sa.String(length=50), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('guidance', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_controls_code'), 'controls', ['code'], unique=True)

    op.create_table(
        'evidence_requirements',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('control_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=300), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('type', sa.String(length=30), nullable=True),
        sa.Column('cadence_days', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['control_id'], ['controls.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'control_references',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('control_id', sa.Integer(), nullable=False),
        sa.Column('framework', sa.String(length=40), nullable=False),
        sa.Column('ref_code', sa.String(length=50), nullable=True),
        sa.Column('title', sa.String(length=300), nullable=True),
        sa.ForeignKeyConstraint(['control_id'], ['controls.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'control_obligations',
        sa.Column('control_id', sa.Integer(), nullable=False),
        sa.Column('obligation_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['control_id'], ['controls.id']),
        sa.ForeignKeyConstraint(['obligation_id'], ['obligations.id']),
        sa.PrimaryKeyConstraint('control_id', 'obligation_id'),
    )

    op.create_table(
        'control_checks',
        sa.Column('control_id', sa.Integer(), nullable=False),
        sa.Column('check_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['control_id'], ['controls.id']),
        sa.ForeignKeyConstraint(['check_id'], ['checks.id']),
        sa.PrimaryKeyConstraint('control_id', 'check_id'),
    )


def downgrade():
    op.drop_table('control_checks')
    op.drop_table('control_obligations')
    op.drop_table('control_references')
    op.drop_table('evidence_requirements')
    op.drop_index(op.f('ix_controls_code'), table_name='controls')
    op.drop_table('controls')
    op.drop_table('obligations')
