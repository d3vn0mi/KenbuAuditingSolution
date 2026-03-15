"""Fix mfa_enabled server default

Revision ID: a1b2c3d4e5f6
Revises: 444bbd1b0fdf
Create Date: 2026-03-15 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '444bbd1b0fdf'
branch_labels = None
depends_on = None


def upgrade():
    # Set existing NULL values to False
    op.execute("UPDATE users SET mfa_enabled = false WHERE mfa_enabled IS NULL")

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('mfa_enabled',
                              existing_type=sa.Boolean(),
                              server_default=sa.text('false'),
                              nullable=False)


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('mfa_enabled',
                              existing_type=sa.Boolean(),
                              server_default=None,
                              nullable=True)
