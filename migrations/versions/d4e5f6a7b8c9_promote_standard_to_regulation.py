"""Promote Standard to Regulation (regulatory layer m1)

Renames standards -> regulations and standard_checks -> regulation_checks, adds
the readiness fields (short_code, status, effective_date, source_url), and
repoints audit_sessions.standard_id -> regulation_id. PostgreSQL-targeted,
matching the existing migration style (dev/test SQLite uses create_all + seed).

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-06-17 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd4e5f6a7b8c9'
down_revision = 'c3d4e5f6a7b8'
branch_labels = None
depends_on = None


def _fk_name(table, column):
    """Find the FK constraint name on table.column.

    The name differs by how the DB was built: an explicit name when created by
    migration b7c8d9e0, but the Postgres auto-name (`<table>_<col>_fkey`) when the
    table came from db.create_all() — which is the entrypoint 'fresh' path. Look it
    up instead of assuming, so `flask db upgrade` works on either origin.
    """
    bind = op.get_bind()
    return bind.execute(sa.text(
        """
        SELECT con.conname
        FROM pg_constraint con
        JOIN pg_attribute a ON a.attrelid = con.conrelid AND a.attnum = ANY(con.conkey)
        WHERE con.conrelid = to_regclass(:tbl) AND con.contype = 'f' AND a.attname = :col
        LIMIT 1
        """
    ), {'tbl': table, 'col': column}).scalar()


def upgrade():
    # 1. Rename the standards table and its slug index.
    op.rename_table('standards', 'regulations')
    op.execute('ALTER INDEX ix_standards_slug RENAME TO ix_regulations_slug')

    # 2. Add the readiness fields.
    op.add_column('regulations', sa.Column('short_code', sa.String(length=20), nullable=True))
    op.add_column('regulations', sa.Column('status', sa.String(length=20), nullable=True))
    op.add_column('regulations', sa.Column('effective_date', sa.Date(), nullable=True))
    op.add_column('regulations', sa.Column('source_url', sa.String(length=500), nullable=True))

    # Backfill sensible defaults for any existing rows.
    op.execute("UPDATE regulations SET status = 'in_force' WHERE status IS NULL")
    op.execute("UPDATE regulations SET short_code = name WHERE short_code IS NULL")

    # 3. Rename the direct mapping table + its column / unique constraint.
    op.rename_table('standard_checks', 'regulation_checks')
    op.alter_column('regulation_checks', 'standard_id', new_column_name='regulation_id')
    op.execute('ALTER TABLE regulation_checks RENAME CONSTRAINT uq_standard_check TO uq_regulation_check')

    # 4. Repoint audit_sessions.standard_id -> regulation_id and rename the FK.
    #    Resolve the actual FK name (explicit vs create_all auto-name) first.
    fk = _fk_name('audit_sessions', 'standard_id')
    op.alter_column('audit_sessions', 'standard_id', new_column_name='regulation_id')
    if fk and fk != 'fk_audit_sessions_regulation':
        op.execute(f'ALTER TABLE audit_sessions RENAME CONSTRAINT "{fk}" TO fk_audit_sessions_regulation')


def downgrade():
    fk = _fk_name('audit_sessions', 'regulation_id')
    op.alter_column('audit_sessions', 'regulation_id', new_column_name='standard_id')
    if fk and fk != 'fk_audit_sessions_standard':
        op.execute(f'ALTER TABLE audit_sessions RENAME CONSTRAINT "{fk}" TO fk_audit_sessions_standard')

    op.execute('ALTER TABLE regulation_checks RENAME CONSTRAINT uq_regulation_check TO uq_standard_check')
    op.alter_column('regulation_checks', 'regulation_id', new_column_name='standard_id')
    op.rename_table('regulation_checks', 'standard_checks')

    op.drop_column('regulations', 'source_url')
    op.drop_column('regulations', 'effective_date')
    op.drop_column('regulations', 'status')
    op.drop_column('regulations', 'short_code')

    op.execute('ALTER INDEX ix_regulations_slug RENAME TO ix_standards_slug')
    op.rename_table('regulations', 'standards')
