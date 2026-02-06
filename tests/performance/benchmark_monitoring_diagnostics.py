import asyncio
import time
import sys
import os
from unittest.mock import MagicMock, patch

# Set required environment variables before importing app modules
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["OPENAI_API_KEY"] = "sk-test-123"
os.environ["AUTH_SECRET"] = "secret"
os.environ["GITHUB_CLIENT_ID"] = "dummy_id"
os.environ["GITHUB_CLIENT_SECRET"] = "dummy_secret"
os.environ["LINKEDIN_CLIENT_ID"] = "dummy_li_id"
os.environ["LINKEDIN_CLIENT_SECRET"] = "dummy_li_secret"
os.environ["ENVIRONMENT"] = "test"

from fastapi import Request

# Ensure app is in path
sys.path.append(os.getcwd())

from app.routes import monitoring as monitoring_module

async def heartbeat_monitor(stop_event):
    """Logs a heartbeat every 0.1s to prove loop is running."""
    count = 0
    while not stop_event.is_set():
        count += 1
        await asyncio.sleep(0.1)
    return count

async def run_benchmark():
    print(">>> Setting up Benchmark for /diagnostics...")

    # Mock DB Session
    mock_db_session = MagicMock()

    # Mock the internal logic to be SLOW and BLOCKING (simulated DB latency)
    def slow_db_execute(*args, **kwargs):
        time.sleep(1.0) # Blocking sleep to simulate slow DB
        return True

    mock_db_session.execute.side_effect = slow_db_execute

    # Context manager support for SessionLocal
    mock_db_session.__enter__.return_value = mock_db_session
    mock_db_session.__exit__.return_value = None

    print(">>> Starting Heartbeat Monitor...")
    stop_event = asyncio.Event()
    monitor_task = asyncio.create_task(heartbeat_monitor(stop_event))

    print(">>> Calling diagnostics() endpoint logic...")
    start_time = time.time()

    # We need to patch 'app.routes.monitoring.httpx.AsyncClient' to avoid real network calls
    # AND patch 'app.routes.monitoring.SessionLocal' to use our mock
    with patch("app.routes.monitoring.httpx.AsyncClient") as mock_client_cls, \
         patch("app.routes.monitoring.SessionLocal", return_value=mock_db_session):

        mock_client = mock_client_cls.return_value.__aenter__.return_value
        mock_client.get.return_value.status_code = 200

        # Run the endpoint
        # No arguments needed now as we removed Depends(get_db)
        await monitoring_module.system_diagnostics()

    end_time = time.time()
    stop_event.set()
    heartbeats = await monitor_task

    duration = end_time - start_time
    print(f"\n>>> Results:")
    print(f"    Total Duration: {duration:.2f}s")
    print(f"    Heartbeats detected: {heartbeats}")

    # Expected: ~10 heartbeats for 1s duration if async/threaded. 0 if blocking.
    if heartbeats >= 5:
        print(">>> ✅ PASS: Event loop remained responsive.")
        return True
    else:
        print(">>> ❌ FAIL: Event loop was blocked.")
        return False

if __name__ == "__main__":
    success = asyncio.run(run_benchmark())
    sys.exit(0 if success else 1)
