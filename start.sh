#!/bin/sh

# Run migrations
alembic upgrade head

# Set port with fallback
PORT=${PORT:-8080}

# Start Uvicorn
uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 4
