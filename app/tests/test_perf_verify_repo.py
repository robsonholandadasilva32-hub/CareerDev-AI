
import pytest
import asyncio
import time
from unittest.mock import MagicMock, patch
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db.session import get_db
from app.core.dependencies import get_user_with_profile
from app.services.social_harvester import social_harvester
from app.services.github_verifier import github_verifier

# --- Mock Setup ---
@pytest.fixture(scope="function")
def mock_db_session():
    session = MagicMock()
    return session

@pytest.fixture(autouse=True)
def override_dependency(mock_db_session):
    app.dependency_overrides[get_db] = lambda: mock_db_session
    # Mock user must be set up inside the test or fixture
    yield
    app.dependency_overrides = {}

@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")

# --- Performance Test ---
@pytest.mark.asyncio
async def test_verify_repo_blocking_baseline(client, mock_db_session):
    """
    Verifies that the current (or intended synchronous) implementation blocks the event loop.
    We verify this by injecting artificial blocking latency into the mocks.
    """

    # 1. Setup Mock User
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.github_username = "perf_user"
    mock_user.streak_count = 5

    # Override dependency
    app.dependency_overrides[get_user_with_profile] = lambda: mock_user

    try:
        # 2. Define Blocking Mocks
        BLOCK_TIME = 0.5  # 500ms blocking

        def blocking_update_streak(*args, **kwargs):
            time.sleep(BLOCK_TIME)

        def blocking_get_recent_commits(*args, **kwargs):
            time.sleep(BLOCK_TIME)
            return [{"id": "1", "message": "fix", "date": "2023-01-01"}]

        # Apply mocks
        # We assume _update_streak_sync is used now instead of direct commit

        with patch('app.routes.dashboard._update_streak_sync', side_effect=blocking_update_streak):

            with patch.object(social_harvester, 'get_recent_commits', side_effect=blocking_get_recent_commits, create=True):

                # Mock verifier to return True so we hit the DB commit path
                with patch.object(github_verifier, 'verify', return_value=True):

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

                    payload = {"language": "python"}
                    response = await client.post("/api/verify/repo", json=payload)

                    max_delay = await monitor_task

                    print(f"DEBUG: Max Event Loop Delay: {max_delay:.4f}s")

                    # 5. Assertions
                    assert response.status_code == 200
                    assert response.json() == {"verified": True}

                    # Verification:
                    # Optimized: max_delay should be small (< 0.1s) even with 1s total blocking time in threads

                    if max_delay < 0.2:
                        print("✅ OPTIMIZATION VERIFIED: Loop is NOT blocked.")
                    else:
                        pytest.fail(f"❌ TEST FAILED: Loop WAS blocked (Max delay: {max_delay:.4f}s). Expected non-blocking.")

    finally:
         app.dependency_overrides = {}
