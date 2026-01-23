import os
import pytest
from unittest.mock import patch, MagicMock
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker

# Mock environment variables BEFORE importing app
os.environ.setdefault("SMTP_HOST", "smtp.example.com")
os.environ.setdefault("SMTP_PORT", "587")
os.environ.setdefault("SMTP_USER", "user")
os.environ.setdefault("SMTP_PASSWORD", "password")
os.environ.setdefault("LINKEDIN_CLIENT_ID", "mock_id")
os.environ.setdefault("LINKEDIN_CLIENT_SECRET", "mock_secret")
os.environ.setdefault("GITHUB_CLIENT_ID", "mock_gh_id")
os.environ.setdefault("GITHUB_CLIENT_SECRET", "mock_gh_secret")

from app.main import app
from app.db.declarative import Base
from app.db.session import get_db
from app.db.models.user import User
from app.core.jwt import create_access_token
# Import models to ensure they are registered
from app.db.models.career import CareerProfile, LearningPlan
from app.db.models.gamification import UserBadge
from app.db.models.security import AuditLog

# Setup In-Memory DB
DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="function")
def db_session():
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(autouse=True)
def patch_middleware_db():
    # Patch the SessionLocal used in AuthMiddleware
    with patch("app.middleware.auth.SessionLocal", TestingSessionLocal):
        yield

@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")

def create_auth_cookie(user_id, email):
    token = create_access_token({"sub": str(user_id), "email": email})
    return {"access_token": token}

@pytest.mark.asyncio
async def test_complete_profile_flow(client, db_session):
    # 1. Create a user who is ready to complete profile
    # (Has LinkedIn and GitHub, but is_profile_completed=False)
    user = User(
        name="Ready User",
        email="ready@example.com",
        hashed_password="pw",
        linkedin_id="L_READY",
        github_id="G_READY",
        is_profile_completed=False,
        terms_accepted=False
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    cookies = create_auth_cookie(user.id, user.email)

    # 2. Form Data
    data = {
        "name": "Updated Name",
        "terms_accepted": "true"
    }

    # 3. POST to /onboarding/complete-profile
    response = await client.post(
        "/onboarding/complete-profile",
        data=data,
        cookies=cookies,
        follow_redirects=False
    )

    # 4. Verify Redirect to Dashboard (303)
    # The code uses 302 by default in RedirectResponse unless customized,
    # but the helper `redirect_to_dashboard` uses 303.
    # Let's check status code.
    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard"

    # 5. Verify DB updates
    db_session.refresh(user)
    assert user.is_profile_completed is True
    assert user.terms_accepted is True
    assert user.name == "Updated Name"

    # 6. Verify Audit Log
    # We need to query the AuditLog table
    audit_log = db_session.query(AuditLog).filter(AuditLog.user_id == user.id).first()
    assert audit_log is not None
    assert audit_log.action == "PROFILE_UPDATE"
