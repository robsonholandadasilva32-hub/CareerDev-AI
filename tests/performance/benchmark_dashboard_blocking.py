import asyncio
import time
import sys
import os
from unittest.mock import MagicMock, patch
from fastapi import Request

# Ensure app is in path
sys.path.append(os.getcwd())

from app.routes import dashboard as dashboard_module
from app.db.models.user import User
from app.db.models.career import CareerProfile

async def heartbeat_monitor(stop_event):
    """Logs a heartbeat every 0.1s to prove loop is running."""
    count = 0
    while not stop_event.is_set():
        count += 1
        # print(f"[Heartbeat] Tick {count}")
        await asyncio.sleep(0.1)
    return count

async def run_benchmark():
    print(">>> Setting up Benchmark...")

    # 1. Mock Data
    mock_db = MagicMock()

    # User with profile
    mock_user = User(id=1, email="test@example.com", streak_count=5)
    mock_profile = CareerProfile()
    mock_profile.github_activity_metrics = {"raw_languages": {"Python": 1000}, "commits_last_30_days": 10}
    mock_profile.linkedin_alignment_data = {"skills": {"Python": 100}}
    mock_profile.skills_graph_data = {}
    mock_profile.market_relevance_score = 80
    mock_user.career_profile = mock_profile

    mock_request = MagicMock(spec=Request)

    # 2. Mock Dependencies
    # Mock career_engine.analyze to be SLOW and BLOCKING (CPU bound simulation)
    def slow_analyze(*args, **kwargs):
        print("    [Engine] Starting heavy analysis (simulated 1.0s block)...")
        time.sleep(1.0) # Blocking sleep
        print("    [Engine] Finished analysis.")
        return {
            "zone_a_radar": {},
            "zone_a_holistic": {"score": 90},
            "weekly_plan": {},
            "skill_confidence": {},
            "career_risks": [],
            "hidden_gems": [],
            "career_forecast": {},
            "benchmark": {},
            "counterfactual": {}
        }

    # Mock get_weekly_history (it's awaited in the route, make it fast async)
    async def fast_history(*args, **kwargs):
        return []

    # Mock templates to avoid rendering
    mock_templates = MagicMock()
    mock_templates.TemplateResponse.return_value = "Rendered HTML"

    # 3. Patch and Execute
    # We patch validate_onboarding_access IN THE DASHBOARD MODULE because of how it is imported
    with patch.object(dashboard_module.career_engine, 'analyze', side_effect=slow_analyze), \
         patch.object(dashboard_module.career_engine, 'get_weekly_history', side_effect=fast_history), \
         patch.object(dashboard_module, 'templates', mock_templates), \
         patch.object(dashboard_module, 'validate_onboarding_access', return_value=None):

        print(">>> Starting Heartbeat Monitor...")
        stop_event = asyncio.Event()
        monitor_task = asyncio.create_task(heartbeat_monitor(stop_event))

        print(">>> Calling dashboard() endpoint logic...")
        start_time = time.time()

        # Call the endpoint handler directly
        await dashboard_module.dashboard(
            request=mock_request,
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
            print(">>> ✅ PASS: Event loop remained responsive.")
            return True
        else:
            print(">>> ❌ FAIL: Event loop was blocked.")
            return False

if __name__ == "__main__":
    success = asyncio.run(run_benchmark())
    sys.exit(0 if success else 1)
