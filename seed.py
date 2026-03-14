#!/usr/bin/env python3
"""Seed the database with platforms, benchmarks, and checks."""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from app.extensions import db
from app.utils.seed import seed_all

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')


def main():
    app = create_app(os.getenv('FLASK_CONFIG', 'development'))

    with app.app_context():
        # Ensure all tables exist (no-op if they already do)
        db.create_all()

        # Run seed
        seed_all(DATA_DIR)
        print('\nSeeding complete!')


if __name__ == '__main__':
    main()
