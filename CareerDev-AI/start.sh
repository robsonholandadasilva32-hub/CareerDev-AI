#!/bin/sh

# Run migrations
alembic upgrade head

# Start Uvicorn
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 4
