#!/bin/bash
set -e

# Check if alembic_version table exists (indicates migrations have been used before)
HAS_ALEMBIC=$(python -c "
from app import create_app
from app.extensions import db
import os, sqlalchemy
app = create_app(os.getenv('FLASK_CONFIG', 'development'))
with app.app_context():
    try:
        db.session.execute(sqlalchemy.text('SELECT 1 FROM alembic_version'))
        print('yes')
    except:
        # Check if any app tables exist (existing DB without migrations)
        try:
            db.session.execute(sqlalchemy.text('SELECT 1 FROM users LIMIT 1'))
            print('legacy')
        except:
            print('fresh')
    finally:
        db.session.rollback()
" 2>/dev/null || echo "fresh")

if [ "$HAS_ALEMBIC" = "fresh" ]; then
    # Brand new database — create all tables from models, then stamp head
    echo "Fresh database detected. Creating schema..."
    python -c "
from app import create_app
from app.extensions import db
import os
app = create_app(os.getenv('FLASK_CONFIG', 'development'))
with app.app_context():
    db.create_all()
    print('Tables created.')
"
    flask db stamp head
elif [ "$HAS_ALEMBIC" = "legacy" ]; then
    # Existing DB created by db.create_all() — run migrations to add new columns
    echo "Legacy database detected. Applying migrations..."
    flask db upgrade
else
    # Normal case — alembic_version exists, apply pending migrations
    flask db upgrade
fi

# Seed database if empty (idempotent — skips if data already exists)
python seed.py

exec "$@"
