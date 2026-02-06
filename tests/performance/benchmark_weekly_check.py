import asyncio
import time
import sys
import os
from unittest.mock import MagicMock, patch
from datetime import datetime

# Ensure app is in path
sys.path.append(os.getcwd())

# --- SET ENV VARS BEFORE IMPORTING APP ---
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["OPENAI_API_KEY"] = "sk-fake-key"
os.environ["AUTH_SECRET"] = "fake-secret"
os.environ["GITHUB_CLIENT_ID"] = "fake-id"
os.environ["GITHUB_CLIENT_SECRET"] = "fake-secret"
os.environ["LINKEDIN_CLIENT_ID"] = "fake-id"
os.environ["LINKEDIN_CLIENT_SECRET"] = "fake-secret"
os.environ["SECRET_KEY"] = "fake-secret-key"
# -----------------------------------------

# --- MOCK HEAVY DEPENDENCIES BEFORE IMPORTING APP ---
# We must mock submodules first, then the top level modules to ensure "from X import Y" works
mock_submodules = [
    "sklearn.linear_model",
    "sklearn.ensemble",
    "sklearn.preprocessing",
    "sklearn.model_selection",
    "sklearn.metrics",
    "sklearn.feature_extraction.text",
    "sklearn.metrics.pairwise",
    "tensorflow.keras",
    "tensorflow.keras.models",
    "tensorflow.keras.layers",
    "tensorflow.keras.optimizers",
    "tensorflow.keras.callbacks",
    "scipy.sparse"
]

mock_top_modules = [
    "tensorflow", "sklearn", "pandas", "openai", "mlflow", "joblib", "numpy",
    "scipy"
]

for mod in mock_submodules:
    sys.modules[mod] = MagicMock()

for mod in mock_top_modules:
    sys.modules[mod] = MagicMock()
# ----------------------------------------------------

# Now we can safely import app modules that might try to import ML libs
from app.routes import dashboard as dashboard_module
from app.db.models.user import User

async def heartbeat_monitor(stop_event):
    """Logs a heartbeat every 0.1s to prove loop is running."""
    count = 0
    while not stop_event.is_set():
        count += 1
        await asyncio.sleep(0.1)
    return count

async def run_benchmark():
    print(">>> Setting up Benchmark for Weekly Check...")

    # 1. Mock Data
    mock_db = MagicMock()
    mock_user = User(id=1, email="test@example.com")

    # 2. Mock the sync helper to be SLOW (simulating DB latency)
    def slow_update_sync(user_id):
        print("    [DB] Starting heavy DB update (simulated 1.0s block)...")
        time.sleep(1.0)  # Blocking sleep
        print("    [DB] Finished DB update.")
        return datetime(2023, 1, 1, 12, 0, 0)

    # 3. Patch and Execute
    # We patch _update_last_weekly_check_sync in the dashboard module
    with patch.object(dashboard_module, '_update_last_weekly_check_sync', side_effect=slow_update_sync):

        print(">>> Starting Heartbeat Monitor...")
        stop_event = asyncio.Event()
        monitor_task = asyncio.create_task(heartbeat_monitor(stop_event))

        print(">>> Calling perform_weekly_check() endpoint logic...")
        start_time = time.time()

        # Call the endpoint handler directly
        await dashboard_module.perform_weekly_check(
            db=mock_db,
            user=mock_user
        )

        end_time = time.time()
        stop_event.set()
        heartbeats = await monitor_task

        duration = end_time - start_time
        print(f"\n>>> Results:")
        print(f"    Total Duration: {duration:.2f}s")
        print(f"    Heartbeats detected: {heartbeats}")

        # Expected: ~10 heartbeats for 1s duration if async. 0 if blocking.
        if heartbeats >= 5:
            print(">>> ✅ PASS: Event loop remained responsive during weekly check.")
            return True
        else:
            print(">>> ❌ FAIL: Event loop was blocked during weekly check.")
            return False

if __name__ == "__main__":
    success = asyncio.run(run_benchmark())
    sys.exit(0 if success else 1)
