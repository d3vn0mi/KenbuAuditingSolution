"""Add OAuth fields to User model

Revision ID: 413d7ecc174b
Revises:
Create Date: 2026-03-13 19:15:14.414371

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '413d7ecc174b'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Use direct ALTER TABLE ADD COLUMN — supported natively by SQLite.
    # Avoids batch_alter_table which causes CircularDependencyError on SQLite
    # when combining multiple add_column + alter_column operations.
    op.add_column('users', sa.Column('auth_provider', sa.String(length=20), nullable=True))
    op.add_column('users', sa.Column('github_id', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('avatar_url', sa.String(length=500), nullable=True))
    op.create_index(op.f('ix_users_github_id'), 'users', ['github_id'], unique=True)


def downgrade():
    op.drop_index(op.f('ix_users_github_id'), table_name='users')
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('avatar_url')
        batch_op.drop_column('github_id')
        batch_op.drop_column('auth_provider')
