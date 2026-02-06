
import pytest
import asyncio
import time
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db.session import get_db
from app.core.dependencies import get_user_with_profile
from app.db.models.user import User

# --- Mock Setup ---
@pytest.fixture(scope="function")
def mock_db_session():
    session = MagicMock()
    return session

@pytest.fixture(autouse=True)
def override_dependency(mock_db_session):
    app.dependency_overrides[get_db] = lambda: mock_db_session
    yield
    app.dependency_overrides = {}

@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")

# --- Performance Test ---
@pytest.mark.asyncio
async def test_weekly_check_blocking_baseline(client, mock_db_session):
    """
    Verifies that the new implementation DOES NOT block the event loop.
    We patch the sync helper to block, and verify that the loop remains responsive.
    """

    # 1. Setup Mock User
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.last_weekly_check = None

    # Override dependency
    app.dependency_overrides[get_user_with_profile] = lambda: mock_user

    try:
        # 2. Define Blocking Mock
        BLOCK_TIME = 0.5  # 500ms blocking

        def blocking_helper(user_id):
            time.sleep(BLOCK_TIME)
            return datetime.now(timezone.utc)

        # Patch the helper function used in dashboard.py
        with patch('app.routes.dashboard._update_last_weekly_check_sync', side_effect=blocking_helper):

            # 3. Background Latency Monitor
            async def latency_monitor():
                delays = []
                for _ in range(10):
                    start = time.perf_counter()
                    await asyncio.sleep(0.1) # Should take 0.1s
                    end = time.perf_counter()
                    delays.append(end - start - 0.1) # Excess delay
                return max(delays)

            # 4. Run Request and Monitor Concurrently
            monitor_task = asyncio.create_task(latency_monitor())

            response = await client.post("/api/dashboard/weekly-check")

            max_delay = await monitor_task

            print(f"DEBUG: Max Event Loop Delay: {max_delay:.4f}s")

            # 5. Assertions
            assert response.status_code == 200
            assert response.json()["status"] == "success"

            # Verification:
            # Optimized: max_delay should be small (< 0.2s) even with 0.5s total blocking time in the helper

            if max_delay < 0.2:
                 print("✅ OPTIMIZATION VERIFIED: Loop is NOT blocked.")
            else:
                 pytest.fail(f"❌ TEST FAILED: Loop WAS blocked (Max delay: {max_delay:.4f}s). Expected non-blocking.")

    finally:
         app.dependency_overrides = {}
