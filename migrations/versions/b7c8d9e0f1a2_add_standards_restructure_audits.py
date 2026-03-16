"""Add standards and restructure audits to multi-asset

Revision ID: b7c8d9e0f1a2
Revises: a1b2c3d4e5f6
Create Date: 2026-03-16 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b7c8d9e0f1a2'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create standards table
    op.create_table('standards',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('slug', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('version', sa.String(length=20), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('slug')
    )
    op.create_index(op.f('ix_standards_slug'), 'standards', ['slug'], unique=True)

    # 2. Create standard_checks table
    op.create_table('standard_checks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('standard_id', sa.Integer(), nullable=False),
        sa.Column('check_id', sa.Integer(), nullable=False),
        sa.Column('article', sa.String(length=50), nullable=True),
        sa.Column('requirement', sa.String(length=300), nullable=True),
        sa.ForeignKeyConstraint(['standard_id'], ['standards.id']),
        sa.ForeignKeyConstraint(['check_id'], ['checks.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('standard_id', 'check_id', name='uq_standard_check')
    )

    # 3. Create audit_assets table
    op.create_table('audit_assets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('asset_type', sa.String(length=50), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['audit_sessions.id']),
        sa.PrimaryKeyConstraint('id')
    )

    # 4. Create audit_asset_benchmarks table
    op.create_table('audit_asset_benchmarks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('asset_id', sa.Integer(), nullable=False),
        sa.Column('benchmark_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['audit_assets.id']),
        sa.ForeignKeyConstraint(['benchmark_id'], ['benchmarks.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('asset_id', 'benchmark_id', name='uq_audit_asset_benchmark')
    )

    # 5. Restructure audit_sessions:
    #    Add new columns
    op.add_column('audit_sessions', sa.Column('title', sa.String(length=200), nullable=True))
    op.add_column('audit_sessions', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('audit_sessions', sa.Column('standard_id', sa.Integer(), nullable=True))
    op.add_column('audit_sessions', sa.Column('created_at', sa.DateTime(), nullable=True))
    op.create_foreign_key('fk_audit_sessions_standard', 'audit_sessions', 'standards', ['standard_id'], ['id'])

    # Migrate data: copy target_name to title, started_at to created_at
    op.execute("UPDATE audit_sessions SET title = COALESCE(target_name, 'Untitled Audit')")
    op.execute("UPDATE audit_sessions SET created_at = started_at")

    # Make title NOT NULL now that data is migrated
    op.alter_column('audit_sessions', 'title', nullable=False)

    # 6. Migrate audit_results to reference audit_assets instead of audit_sessions.
    #    For each existing session, create an audit_asset from the session's target info,
    #    then update results to point to the new asset.
    op.execute("""
        INSERT INTO audit_assets (session_id, name, asset_type, ip_address)
        SELECT id, COALESCE(target_name, 'Unknown'), 'Server', target_ip
        FROM audit_sessions
    """)

    # Also create audit_asset_benchmarks for the migrated assets
    op.execute("""
        INSERT INTO audit_asset_benchmarks (asset_id, benchmark_id)
        SELECT aa.id, s.benchmark_id
        FROM audit_assets aa
        JOIN audit_sessions s ON s.id = aa.session_id
        WHERE s.benchmark_id IS NOT NULL
    """)

    # Add asset_id column to audit_results
    op.add_column('audit_results', sa.Column('asset_id', sa.Integer(), nullable=True))

    # Map results from session_id to asset_id
    op.execute("""
        UPDATE audit_results SET asset_id = (
            SELECT aa.id FROM audit_assets aa
            WHERE aa.session_id = audit_results.session_id
            LIMIT 1
        )
    """)

    # Drop old unique constraint and session_id FK
    op.drop_constraint('uq_session_check', 'audit_results', type_='unique')
    op.drop_column('audit_results', 'session_id')

    # Make asset_id NOT NULL and add new FK + unique constraint
    op.alter_column('audit_results', 'asset_id', nullable=False)
    op.create_foreign_key('fk_audit_results_asset', 'audit_results', 'audit_assets', ['asset_id'], ['id'])
    op.create_unique_constraint('uq_audit_asset_check', 'audit_results', ['asset_id', 'check_id'])

    # Drop old columns from audit_sessions
    op.drop_constraint('audit_sessions_benchmark_id_fkey', 'audit_sessions', type_='foreignkey')
    op.drop_column('audit_sessions', 'benchmark_id')
    op.drop_column('audit_sessions', 'target_name')
    op.drop_column('audit_sessions', 'target_ip')


def downgrade():
    # Add back old columns to audit_sessions
    op.add_column('audit_sessions', sa.Column('target_ip', sa.String(length=45), nullable=True))
    op.add_column('audit_sessions', sa.Column('target_name', sa.String(length=200), nullable=True))
    op.add_column('audit_sessions', sa.Column('benchmark_id', sa.Integer(), nullable=True))
    op.create_foreign_key('audit_sessions_benchmark_id_fkey', 'audit_sessions', 'benchmarks', ['benchmark_id'], ['id'])

    # Migrate data back from assets to sessions
    op.execute("""
        UPDATE audit_sessions SET
            target_name = (SELECT aa.name FROM audit_assets aa WHERE aa.session_id = audit_sessions.id LIMIT 1),
            target_ip = (SELECT aa.ip_address FROM audit_assets aa WHERE aa.session_id = audit_sessions.id LIMIT 1),
            benchmark_id = (
                SELECT aab.benchmark_id FROM audit_asset_benchmarks aab
                JOIN audit_assets aa ON aa.id = aab.asset_id
                WHERE aa.session_id = audit_sessions.id LIMIT 1
            )
    """)

    # Re-add session_id to audit_results
    op.add_column('audit_results', sa.Column('session_id', sa.Integer(), nullable=True))
    op.execute("""
        UPDATE audit_results SET session_id = (
            SELECT aa.session_id FROM audit_assets aa
            WHERE aa.id = audit_results.asset_id
        )
    """)

    # Drop new constraints and column
    op.drop_constraint('uq_audit_asset_check', 'audit_results', type_='unique')
    op.drop_constraint('fk_audit_results_asset', 'audit_results', type_='foreignkey')
    op.drop_column('audit_results', 'asset_id')

    op.alter_column('audit_results', 'session_id', nullable=False)
    op.create_unique_constraint('uq_session_check', 'audit_results', ['session_id', 'check_id'])
    op.create_foreign_key(None, 'audit_results', 'audit_sessions', ['session_id'], ['id'])

    # Drop new columns from audit_sessions
    op.drop_constraint('fk_audit_sessions_standard', 'audit_sessions', type_='foreignkey')
    op.drop_column('audit_sessions', 'created_at')
    op.drop_column('audit_sessions', 'standard_id')
    op.drop_column('audit_sessions', 'description')
    op.drop_column('audit_sessions', 'title')

    # Drop new tables
    op.drop_table('audit_asset_benchmarks')
    op.drop_table('audit_assets')
    op.drop_table('standard_checks')
    op.drop_index(op.f('ix_standards_slug'), table_name='standards')
    op.drop_table('standards')
