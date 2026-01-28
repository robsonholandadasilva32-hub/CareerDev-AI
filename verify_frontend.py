import os
import sys
import asyncio
from datetime import datetime
from sqlalchemy.orm import Session

# Add app to path
sys.path.append(os.getcwd())

from app.db.session import SessionLocal, engine
# Import Base to register all models to avoid relationship errors
from app.db.base import Base
from app.db.models.user import User
from app.db.models.career import CareerProfile
from app.core.jwt import create_access_token
from app.services.security_service import create_user_session
from app.core.config import settings

from playwright.sync_api import sync_playwright, expect

def setup_user(db: Session):
    email = "verification_user@example.com"
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            name="Verification User",
            email=email,
            hashed_password="hashed_dummy_password",
            email_verified=True,
            terms_accepted=True,
            is_profile_completed=True,
            weekly_streak_count=4, # Hardcore Mode Active
            github_id="12345", # Needed to avoid onboarding redirect
            linkedin_id="67890" # Needed to avoid onboarding redirect
        )
        db.add(user)
        db.commit()

        # Add Profile
        profile = CareerProfile(
            user_id=user.id,
            target_role="Rust Engineer",
            github_activity_metrics={"raw_languages": {"Python": 100}, "commits_last_30_days": 15},
            skills_snapshot={"Python": 80}
        )
        db.add(profile)
        db.commit()
    else:
        # Update streak
        user.weekly_streak_count = 4
        user.is_profile_completed = True
        user.terms_accepted = True
        if not user.career_profile:
             profile = CareerProfile(user_id=user.id)
             db.add(profile)

        db.commit()

    # Create Session
    sid = create_user_session(db, user.id, "127.0.0.1", "Playwright-Verification")
    token = create_access_token({"sub": str(user.id), "email": user.email, "sid": sid})
    return token

def run_verification():
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        token = setup_user(db)
    finally:
        db.close()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()

        # Set Cookie
        context.add_cookies([{
            "name": "access_token",
            "value": token,
            "domain": "localhost",
            "path": "/"
        }])

        page = context.new_page()

        # Navigate to Dashboard
        print("Navigating to Dashboard...")
        page.goto("http://localhost:8000/dashboard")

        # Wait for loading
        page.wait_for_load_state("networkidle")

        # Check for Streak Widget
        print("Checking Streak Widget...")
        expect(page.locator("#streak-widget")).to_be_visible()

        # Check for Hardcore Fire
        expect(page.locator(".streak-square.hardcore")).to_have_count(4)

        # Screenshot Audit View
        print("Screenshotting Audit View...")
        if not os.path.exists("verification"): os.makedirs("verification")
        page.screenshot(path="verification/dashboard_audit.png")

        # Click Weekly Plan Tab
        print("Switching to Weekly Plan...")
        page.click("#tab-growth")

        # Wait for content
        page.wait_for_selector("#view-growth")

        # Screenshot Weekly Plan
        print("Screenshotting Weekly Plan...")
        page.screenshot(path="verification/dashboard_plan.png")

        # Verify Content in Plan
        expect(page.locator("text=FOCUS:")).to_be_visible()

        # Close
        browser.close()
        print("Verification Complete.")

if __name__ == "__main__":
    run_verification()
