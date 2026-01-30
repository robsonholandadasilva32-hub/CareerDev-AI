
import asyncio
import time
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, MagicMock
from app.main import app
from app.core.jwt import create_access_token

# Mock the database session to sleep
def mock_slow_query(*args, **kwargs):
    time.sleep(1.0)  # Blocking sleep!
    return MagicMock(first=lambda: None) # Return None to avoid further logic

@pytest.mark.asyncio
async def test_middleware_blocking():
    # Setup: Create a token so middleware triggers DB logic
    token = create_access_token({"sub": "1", "sid": "session_123"})
    cookies = {"access_token": token}

    # We need to patch SessionLocal in the middleware module
    # We'll make db.query sleep

    mock_session = MagicMock()
    # When db.query(...) is called, it returns a mock object
    # We want the sleep to happen when this chain is executed.
    # The code does: db.query(UserSession).filter(...).first()
    # Let's put the sleep in `query` for simplicity
    mock_session.query.side_effect = mock_slow_query

    with patch("app.middleware.auth.SessionLocal", return_value=mock_session):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:

            print("\nStarting concurrent requests...")
            start_time = time.time()

            # Task 1: Protected endpoint that triggers auth (and thus the sleep)
            # We use a non-existent endpoint or just verify /health with token?
            # If we hit /health with token, middleware still runs.
            # But let's use a dummy path to be sure we aren't confusing things,
            # though middleware runs for everything.
            # Let's use /api/dashboard which is protected/valid path prefix usually.
            task_auth = asyncio.create_task(client.get("/api/dashboard", cookies=cookies))

            # Small delay to ensure task_auth starts and hits the sleep
            await asyncio.sleep(0.1)

            # Task 2: Health check (should be fast if not blocked)
            task_health = asyncio.create_task(client.get("/health"))

            # Wait for health
            response_health = await task_health
            end_health = time.time()

            # Wait for auth (it might fail 404/403 but that's fine)
            await task_auth

            health_duration = end_health - start_time
            print(f"Health request took: {health_duration:.4f}s")

            # If blocked, health_duration should be > 1.0s (plus the 0.1s delay)
            # If non-blocking, it should be close to 0.1s

            if health_duration > 1.0:
                print("⚠️  BASELINE CONFIRMED: Event loop was blocked.")
            else:
                print("✅  OPTIMIZED: Event loop was NOT blocked.")

            return health_duration
