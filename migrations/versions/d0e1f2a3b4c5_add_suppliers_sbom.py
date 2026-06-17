"""Add supplier register + SBOM intake (m9, CSA2)

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-06-17 03:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'd0e1f2a3b4c5'
down_revision = 'c9d0e1f2a3b4'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'suppliers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('contact', sa.String(length=200), nullable=True),
        sa.Column('country', sa.String(length=100), nullable=True),
        sa.Column('criticality', sa.String(length=20), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'sboms',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('supplier_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=True),
        sa.Column('format', sa.String(length=20), nullable=True),
        sa.Column('original_filename', sa.String(length=300), nullable=True),
        sa.Column('component_count', sa.Integer(), nullable=True),
        sa.Column('raw_size', sa.Integer(), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'sbom_components',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sbom_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=300), nullable=False),
        sa.Column('version', sa.String(length=100), nullable=True),
        sa.Column('purl', sa.String(length=500), nullable=True),
        sa.Column('license', sa.String(length=200), nullable=True),
        sa.ForeignKeyConstraint(['sbom_id'], ['sboms.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'supplier_controls',
        sa.Column('supplier_id', sa.Integer(), nullable=False),
        sa.Column('control_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id']),
        sa.ForeignKeyConstraint(['control_id'], ['controls.id']),
        sa.PrimaryKeyConstraint('supplier_id', 'control_id'),
    )


def downgrade():
    op.drop_table('supplier_controls')
    op.drop_table('sbom_components')
    op.drop_table('sboms')
    op.drop_table('suppliers')
