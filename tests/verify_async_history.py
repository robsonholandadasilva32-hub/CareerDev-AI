import asyncio
import time
from unittest.mock import MagicMock, patch
import sys
import os

# Add repo root to path
sys.path.append(os.getcwd())

from app.services.career_engine import career_engine
from app.db.models.user import User

async def main():
    # Mock User and Session
    mock_db = MagicMock()
    mock_user = User(id=1, email="test@test.com")

    def slow_sync_method(db, user_id):
        print("    [Thread] Starting slow sync operation...")
        time.sleep(1) # Block the thread for 1 second
        print("    [Thread] Finished slow sync operation.")
        return [{"week": 1, "focus": "Test"}]

    # Patch the method on the instance
    with patch.object(career_engine, '_get_weekly_history_sync', side_effect=slow_sync_method):
        print("Starting async test...")
        start_time = time.time()

        # Start the "heavy" task
        task = asyncio.create_task(career_engine.get_weekly_history(mock_db, mock_user))

        # Run a "heartbeat" task to prove loop is free
        heartbeat_count = 0
        while not task.done():
            heartbeat_count += 1
            await asyncio.sleep(0.1)
            print(f"Heartbeat {heartbeat_count}")

        result = await task
        end_time = time.time()

        print(f"Task finished in {end_time - start_time:.2f}s")
        print(f"Heartbeats: {heartbeat_count}")

        # If the main loop was blocked, we wouldn't see heartbeats roughly every 0.1s
        # Since the task takes 1s, we expect ~10 heartbeats.
        # If it was blocking, we would see 0 heartbeats (or maybe 1 if scheduled before).

        if heartbeat_count >= 8:
            print("SUCCESS: Event loop remained responsive.")
        else:
            print(f"FAILURE: Event loop was blocked (Heartbeats: {heartbeat_count}).")

if __name__ == "__main__":
    asyncio.run(main())
