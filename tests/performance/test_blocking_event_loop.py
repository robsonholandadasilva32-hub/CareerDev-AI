import pytest
import asyncio
import time
from unittest.mock import MagicMock
from app.routes.dashboard import perform_weekly_check, verify_repo
from app.db.models.user import User

@pytest.mark.asyncio
async def test_perform_weekly_check_blocking_behavior():
    """
    Verifies that the database commit does not block the event loop.
    Regression test for perform_weekly_check optimization.
    """
    mock_db = MagicMock()

    # Simulate a slow blocking commit
    BLOCK_TIME = 0.5
    def blocking_commit():
        time.sleep(BLOCK_TIME)

    mock_db.commit.side_effect = blocking_commit

    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.email = "perf@test.com"

    heartbeat_timestamps = []
    async def heartbeat():
        end_time = time.time() + (BLOCK_TIME * 2)
        while time.time() < end_time:
            heartbeat_timestamps.append(time.time())
            await asyncio.sleep(0.05)

    task = asyncio.create_task(heartbeat())
    await asyncio.sleep(0.05)

    await perform_weekly_check(db=mock_db, user=mock_user)

    await task

    gaps = []
    for i in range(1, len(heartbeat_timestamps)):
        gaps.append(heartbeat_timestamps[i] - heartbeat_timestamps[i-1])

    max_gap = max(gaps) if gaps else 0

    # If blocking, max_gap would be >= BLOCK_TIME (0.5)
    # With optimization, it should be small (around sleep interval 0.05)
    assert max_gap < (BLOCK_TIME * 0.5), f"Event loop blocked for {max_gap:.4f}s"

@pytest.mark.asyncio
async def test_verify_repo_blocking_behavior():
    """
    Verifies that the database commit in verify_repo does not block the event loop.
    Regression test for verify_repo optimization.
    """
    mock_db = MagicMock()

    BLOCK_TIME = 0.5
    def blocking_commit():
        time.sleep(BLOCK_TIME)

    mock_db.commit.side_effect = blocking_commit

    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.email = "perf@test.com"
    mock_user.github_username = "testuser"
    mock_user.streak_count = 0

    payload = {"language": "Python"}

    # Use raising=False because the method might be missing in some versions/mocks
    with pytest.MonkeyPatch.context() as m:
        m.setattr("app.routes.dashboard.social_harvester.get_recent_commits", lambda x: [], raising=False)
        m.setattr("app.routes.dashboard.github_verifier.verify", lambda x, y: True)

        heartbeat_timestamps = []
        async def heartbeat():
            end_time = time.time() + (BLOCK_TIME * 2)
            while time.time() < end_time:
                heartbeat_timestamps.append(time.time())
                await asyncio.sleep(0.05)

        task = asyncio.create_task(heartbeat())
        await asyncio.sleep(0.05)

        await verify_repo(payload=payload, db=mock_db, user=mock_user)

        await task

        gaps = []
        for i in range(1, len(heartbeat_timestamps)):
            gaps.append(heartbeat_timestamps[i] - heartbeat_timestamps[i-1])

        max_gap = max(gaps) if gaps else 0

        assert max_gap < (BLOCK_TIME * 0.5), f"Event loop blocked for {max_gap:.4f}s"
