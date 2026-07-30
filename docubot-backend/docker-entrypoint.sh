#!/bin/sh
set -e

echo "Running database migrations (alembic upgrade head)..."
alembic upgrade head || { echo "Database migration failed!"; exit 1; }

echo "Starting Uvicorn web server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8001 "$@"
