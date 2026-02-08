from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import uvicorn
import threading
import time
from playwright.sync_api import sync_playwright
import os

# Ensure we are in the root directory so app/templates is found
if not os.path.exists("app/templates"):
    print("Error: Run this script from the project root")
    exit(1)

app = FastAPI()
templates = Jinja2Templates(directory="app/templates")

# Mock User
class MockUser:
    email = "test@example.com"
    streak_count = 5
    is_admin = False # Required by layout? Maybe not.

# Mock Career Data with Early Warning
career_data = {
    "early_warning": {
        "type": "SPIKE",
        "level": "CRITICAL",
        "delta": 20,
        "message": "⚠️ Sudden Risk Spike: +20% since last check."
    },
    "career_forecast": {
        "risk_level": "HIGH",
        "risk_score": 85,
        "rule_risk": 80,
        "ml_risk": 90,
        "model_version": "1.0",
        "experiment": "A"
    },
    "weekly_plan": {
        "focus": "Python",
        "mode": "GROWTH",
        "tasks": []
    },
    "skill_confidence": {"Python": 80, "Rust": 60},
    "zone_a_radar": {
        "labels": ["Python", "Rust"],
        "datasets": [{"data": [80, 60]}]
    },
    "shap_visual": {
        "labels": ["Commit Velocity", "Skill Gap"],
        "values": [10, 20]
    },
    "risk_timeline": {
        "labels": ["Jan", "Feb"],
        "data_points": [50, 70]
    },
    "benchmark": None,
    "team_benchmark": None,
    "team_health": None,
    "team_burnout": None,
    "exit_simulation": None,
    "career_risks": [],
    "hidden_gems": [],
    "multi_week_plan": None
}

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    # Mocking request.state.user if needed by layout
    request.state.user = MockUser()
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": MockUser(),
            "market_score": 75,
            "user_streak": 5,
            "career_data": career_data,
            "weekly_history": [],
            "greeting_message": "Hello!"
        }
    )

def start_server():
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="error")

if __name__ == "__main__":
    # Start server in background thread
    print("Starting server...")
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    time.sleep(3) # Give it time to start

    print("Launching Playwright...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto("http://127.0.0.1:8000/dashboard")
            # Wait for the alert to be visible
            page.wait_for_selector("text=CRITICAL RISK SPIKE DETECTED", timeout=5000)

            # Take screenshot
            page.screenshot(path="/home/jules/verification/dashboard_alert.png", full_page=True)
            print("Screenshot saved to /home/jules/verification/dashboard_alert.png")
        except Exception as e:
            print(f"Error: {e}")
            # Take screenshot anyway to debug
            page.screenshot(path="/home/jules/verification/error_debug.png", full_page=True)
        finally:
            browser.close()
