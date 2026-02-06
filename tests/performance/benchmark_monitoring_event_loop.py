import pytest
import asyncio
import time
from httpx import AsyncClient, ASGITransport
from unittest.mock import MagicMock
from app.main import app
from app.db.session import get_db

# Mock DB Session that blocks on execute
def mock_blocking_execute(*args, **kwargs):
    time.sleep(1.0) # Blocking sleep for 1 second
    return MagicMock()

@pytest.fixture
def mock_slow_db():
    mock_session = MagicMock()
    mock_session.execute.side_effect = mock_blocking_execute
    return mock_session

@pytest.fixture
def client_with_slow_db(mock_slow_db):
    app.dependency_overrides[get_db] = lambda: mock_slow_db
    yield AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_monitoring_event_loop_responsiveness(client_with_slow_db):
    """
    Verifies that the /diagnostics endpoint does not block the event loop
    even when the database check is slow (simulated by time.sleep(1.0)).
    """
    print("\nStarting Heartbeat Test...")

    # 1. Start a heartbeat task to measure loop lag
    async def heartbeat():
        lags = []
        # Monitor for slightly longer than the blocking operation
        for _ in range(15):
            start = time.perf_counter()
            await asyncio.sleep(0.1)
            end = time.perf_counter()
            lag = end - start - 0.1
            lags.append(lag)
        return max(lags) if lags else 0.0

    heartbeat_task = asyncio.create_task(heartbeat())

    # 2. Hit the diagnostics endpoint
    # The DB check inside should take ~1s (mocked sleep)
    start_req = time.perf_counter()
    response = await client_with_slow_db.get("/api/v1/monitoring/diagnostics")
    end_req = time.perf_counter()

    # 3. Wait for heartbeat to finish
    max_lag = await heartbeat_task

    print(f"Request Duration: {end_req - start_req:.4f}s")
    print(f"Max Event Loop Lag: {max_lag:.4f}s")

    # Assertions
    assert response.status_code == 200

    # If blocking, lag would be > 1.0s (since time.sleep(1.0) blocks the thread running the loop)
    # If non-blocking (offloaded to thread), lag should be small.
    # We use 0.5s as a safe threshold (allowing for some environment noise),
    # but typically it should be < 0.05s.
    assert max_lag < 0.5, f"Event loop was blocked! Max lag: {max_lag:.4f}s"

    data = response.json()
    assert data["database"] == "connected"
