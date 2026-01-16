# Run migrations
alembic upgrade head

# Start Uvicorn with PORT env var support
# Defaults to 10000 if PORT not set
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000} --workers 4
