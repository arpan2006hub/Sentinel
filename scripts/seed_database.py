#!/usr/bin/env python3
"""
seed_database.py — Placeholder

This script will eventually:
1. Connect to PostgreSQL (using DATABASE_URL from environment)
2. Run Alembic migrations to create tables
3. Optionally seed with initial data (admin user, default case, etc.)

Currently NOT IMPLEMENTED.

Usage (future):
    python scripts/seed_database.py

Requirements:
    - psycopg2
    - alembic
    - SQLAlchemy models defined in backend/app/models/
"""

import os
import sys

def main():
    print("[seed_database] NOT YET IMPLEMENTED")
    print("[seed_database] This script will:")
    print("  1. Run database migrations (Alembic)")
    print("  2. Seed initial data if needed")
    print("")
    print("Required:")
    print("  - DATABASE_URL environment variable")
    print("  - SQLAlchemy models in backend/app/models/")
    print("  - Alembic configuration")
    sys.exit(1)

if __name__ == "__main__":
    main()