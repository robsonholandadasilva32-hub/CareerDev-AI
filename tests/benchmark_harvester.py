import asyncio
import time
import logging
from unittest.mock import MagicMock, patch
from app.services.social_harvester import social_harvester

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("benchmark")

async def heartbeat(duration: float, interval: float = 0.1):
    """
    Ticks every `interval` seconds for `duration`.
    Returns the number of ticks.
    """
    ticks = 0
    end_time = time.time() + duration
    while time.time() < end_time:
        ticks += 1
        await asyncio.sleep(interval)
    return ticks

def blocking_sleep(seconds: float):
    """Simulates a blocking synchronous operation (like a heavy DB query)."""
    time.sleep(seconds)
    return True

async def run_benchmark():
    print("⚡ Starting Harvester Benchmark...")

    # We simulate 1 second of blocking work (2x 0.5s calls)
    mock_sleep_time = 0.5
    total_expected_duration = mock_sleep_time * 2

    # Patch the sync methods that are supposed to be offloaded
    # We use side_effect to inject real blocking sleep
    with patch.object(social_harvester, "_ensure_profile_exists_sync", side_effect=lambda *args: (blocking_sleep(mock_sleep_time) and "Dev", None)) as mock_ensure, \
         patch.object(social_harvester, "_save_github_data_sync", side_effect=lambda *args: blocking_sleep(mock_sleep_time)) as mock_save, \
         patch.object(social_harvester, "_harvest_github_raw", new_callable=MagicMock) as mock_harvest_raw:

        # Mock the async harvest raw to return immediately
        async def async_return(*args):
             return ({"Python": 100}, {})
        mock_harvest_raw.side_effect = async_return

        # Start the Heartbeat
        # We run it for slightly longer than the task
        heartbeat_task = asyncio.create_task(heartbeat(total_expected_duration + 0.2))

        start_time = time.time()

        # Run the Harvester
        await social_harvester.harvest_github_data(user_id=1, token="test_token")

        elapsed = time.time() - start_time
        ticks = await heartbeat_task

        print(f"⏱️  Total Time: {elapsed:.2f}s")
        print(f"💓 Heartbeat Ticks: {ticks} (Expected ~{int(total_expected_duration / 0.1)})")

        # Analysis
        # If blocking: Ticks would be ~0 or 1 (loop blocked during sleeps)
        # If non-blocking: Ticks would be ~10

        if ticks >= 8:
            print("✅ PASS: Event Loop remained responsive.")
        else:
            print("❌ FAIL: Event Loop was blocked!")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
