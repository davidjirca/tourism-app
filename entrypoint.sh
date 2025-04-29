#!/bin/bash
set -e

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to start..."
while ! nc -z postgres 5432; do
  sleep 1
done
echo "PostgreSQL started"

# Wait for Redis to be ready
echo "Waiting for Redis to start..."
while ! nc -z redis 6379; do
  sleep 1
done
echo "Redis started"

# Run database migrations or initialization if needed
python -c "from app.db.init_db import create_tables, initialize_destinations; from app.db.session import SessionLocal; db = SessionLocal(); create_tables(); initialize_destinations(db); db.close()"
echo "Database initialized"

# Execute the command provided as arguments to this script
exec "$@"