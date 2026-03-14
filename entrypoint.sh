#!/bin/bash
set -e

# Apply any pending database migrations
flask db upgrade

# Seed database if empty (idempotent — skips if data already exists)
python seed.py

exec "$@"
