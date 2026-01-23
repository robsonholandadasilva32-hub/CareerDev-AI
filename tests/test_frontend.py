import pytest
from playwright.sync_api import Page, expect
import time
import random
import re
from datetime import datetime
from app.db.session import SessionLocal
# Import all models to ensure relationships are resolved
from app.db.models.user import User
from app.db.models.security import UserSession, AuditLog
from app.db.models.career import CareerProfile, LearningPlan
from app.db.models.gamification import UserBadge
from app.core.jwt import create_access_token

# Helper to setup a user directly in the DB
def setup_verified_user(db):
    # Use unique email and IDs to avoid collisions
    timestamp = int(time.time())
    rand = random.randint(1000, 9999)
    email = f"billing_test_{timestamp}_{rand}@example.com"

    user = User(
        name="Billing Test User",
        email=email,
        hashed_password="mock_hash_bypass", # Direct hash inject to avoid passlib issues
        email_verified=True,
        is_profile_completed=True, # Critical to avoid Onboarding redirect loop
        linkedin_id=f"li_{timestamp}_{rand}",
        github_id=f"gh_{timestamp}_{rand}",
        created_at=datetime.utcnow()
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def test_billing_page_access_via_cookie_bypass(page: Page):
    """
    Verifies the Billing Page by bypassing the login UI and injecting a valid session cookie.
    Checks for:
    1. Successful access (no redirect to login)
    2. Presence of specific Portuguese text.
    3. Presence of Stripe Elements container.
    """
    db = SessionLocal()
    try:
        # 1. Setup User
        user = setup_verified_user(db)

        # 2. Create Session (Required for AuthMiddleware)
        session = UserSession(
            user_id=user.id,
            ip_address="127.0.0.1",
            user_agent="Playwright Test Runner",
            last_active_at=datetime.utcnow(),
            is_active=True
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        # 3. Generate Valid JWT
        token = create_access_token({
            "sub": str(user.id),
            "email": user.email,
            "sid": str(session.id)
        })

        # 4. Inject Cookie into Browser Context
        page.context.add_cookies([{
            "name": "access_token",
            "value": token,
            "domain": "localhost",
            "path": "/",
            "httpOnly": True,
            "secure": False,
            "sameSite": "Lax"
        }])

        # 5. Navigate to Billing Page
        # Using the direct route alias
        page.goto("http://localhost:8000/subscription/checkout")

        # 6. Assertions

        # Should NOT be redirected to login
        expect(page).not_to_have_url(re.compile(".*login.*"))

        # Should contain the specific Portuguese text requested
        expect(page.locator("body")).to_contain_text("Algumas funcionalidades são disponibilizadas gratuitamente.")

        # Should show the Stripe Payment Element container
        expect(page.locator("#payment-element")).to_be_visible()

    finally:
        db.close()
