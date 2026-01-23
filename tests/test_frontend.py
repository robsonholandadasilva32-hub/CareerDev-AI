import pytest
from playwright.sync_api import Page, expect
import time
import random
import re
import uuid
from app.db.session import SessionLocal
from app.db.models.user import User
# The following imports are required to register models with SQLAlchemy
# and prevent InvalidRequestError during User mapper initialization
from app.db.models.career import CareerProfile, LearningPlan
from app.db.models.security import AuditLog, UserSession
from app.db.models.gamification import UserBadge
from app.services.security_service import create_user_session
from app.core.jwt import create_access_token

def create_authenticated_user(db, email: str):
    """
    Creates a verified user in the DB and returns a valid access token.
    """
    # Create User
    user = User(
        email=email,
        name="Test User",
        hashed_password="mock_password_hash", # We won't login via password, so this is fine
        is_profile_completed=True,
        terms_accepted=True,
        email_verified=True, # Bypass email verification
        subscription_status='free',
        linkedin_id=f"li_{uuid.uuid4()}", # Unique ID to satisfy constraints
        github_id=f"gh_{uuid.uuid4()}"
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create Session
    session_id = create_user_session(db, user.id, "127.0.0.1", "Playwright Test")

    # Generate Token
    token = create_access_token(
        data={"sub": str(user.id), "sid": session_id}
    )
    return token

def test_user_flow(page: Page):
    # Setup DB
    db = SessionLocal()
    email = f"test_{int(time.time())}_{random.randint(1000,9999)}@example.com"

    try:
        # Create Authenticated User (Bypass Registration/Verification)
        token = create_authenticated_user(db, email)

        # Inject Cookie
        # Note: We must navigate to the domain first or set url in add_cookies?
        # Playwright add_cookies works for the context.
        page.context.add_cookies([{
            "name": "access_token",
            "value": token,
            "domain": "localhost",
            "path": "/"
        }])

        # 1. Dashboard - Check Trial Banner (Free Tier)
        # Navigate to Dashboard directly (Bypassing Login)
        page.goto("http://localhost:8000/dashboard")

        # Verify we are on dashboard (auth worked)
        expect(page).to_have_url(re.compile(".*dashboard.*"))

        # Check for the trial notice banner (English version as per base.html)
        # "Some features are available for free." inside a yellow box (#fbbf24)
        notice = page.locator("div", has_text="Some features are available for free")
        expect(notice).to_be_visible()

        # 2. Billing Page
        # Navigate to Billing (actually /subscription/upgrade)
        page.goto("http://localhost:8000/subscription/upgrade")

        # Verify Billing Page Content
        # Looking for common billing elements
        expect(page.locator("body")).to_contain_text("Subscribe Premium")

    finally:
        db.close()
