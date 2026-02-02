import os
import sys
from playwright.sync_api import sync_playwright
from sqlalchemy.orm import Session

# Add app to path to import utils
sys.path.append(os.getcwd())
# Ensure all models are loaded
from app.db.base import Base
from app.core.security import create_access_token
from app.db.session import SessionLocal
from app.db.models.user import User

def create_test_user():
    db = SessionLocal()
    user = db.query(User).filter(User.email == "test@example.com").first()
    if not user:
        user = User(
            email="test@example.com",
            hashed_password="dummy_password_hash",
            full_name="Test User",
            is_active=True,
            is_profile_completed=True, # Bypass onboarding
            linkedin_id="test_li",
            github_id="test_gh",
            terms_accepted=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    db.close()
    return user

def verify_dashboard_nav():
    user = create_test_user()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()

        # Generate Token
        token = create_access_token({"sub": str(user.id), "email": user.email})

        # Set Cookie
        context.add_cookies([{
            "name": "access_token",
            "value": token,
            "domain": "localhost",
            "path": "/"
        }])

        page = context.new_page()
        try:
            page.goto("http://localhost:8001/dashboard")
            # Wait for nav-dock
            page.wait_for_selector(".nav-dock")

            # Screenshot
            os.makedirs("/home/jules/verification", exist_ok=True)
            page.screenshot(path="/home/jules/verification/dashboard_nav.png")
            print("Screenshot taken.")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    verify_dashboard_nav()
