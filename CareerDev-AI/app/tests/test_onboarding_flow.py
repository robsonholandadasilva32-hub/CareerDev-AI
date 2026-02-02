import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Set env vars required for app startup
os.environ.setdefault("SMTP_HOST", "smtp.example.com")
os.environ.setdefault("SMTP_PORT", "587")
os.environ.setdefault("SMTP_USER", "user")
os.environ.setdefault("SMTP_PASSWORD", "password")
os.environ.setdefault("LINKEDIN_CLIENT_ID", "mock_id")
os.environ.setdefault("LINKEDIN_CLIENT_SECRET", "mock_secret")
os.environ.setdefault("GITHUB_CLIENT_ID", "mock_gh_id")
os.environ.setdefault("GITHUB_CLIENT_SECRET", "mock_gh_secret")

from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.db.models.user import User
# Ensure all models are loaded for relationships
from app.db.models.career import CareerProfile, LearningPlan
from app.db.models.gamification import UserBadge
from app.core.jwt import create_access_token

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

@pytest.fixture(autouse=True)
def override_dependency():
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides = {}

@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(autouse=True)
def patch_middleware_db():
    # Patch the SessionLocal used in AuthMiddleware to use our Test DB
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
async def test_github_linking_flow(client, db_session):
    # 1. Create User with LinkedIn only
    user = User(
        name="LinkedIn User",
        email="linked@example.com",
        hashed_password="pw",
        linkedin_id="L123",
        is_profile_completed=False
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # 2. Login as this user
    cookies = create_auth_cookie(user.id, user.email)

    # 3. Simulate GitHub Callback
    mock_token = {'access_token': 'fake_gh_token', 'token_type': 'bearer'}
    mock_user_info = {
        'id': 999,
        'login': 'ghuser',
        'email': 'linked@example.com', # Matches
        'name': 'GH User',
        'avatar_url': 'http://avatar.url/gh.jpg'
    }

    with patch('app.routes.social.oauth.github.fetch_access_token', new_callable=AsyncMock) as mock_fetch, \
         patch('app.routes.social.oauth.github.get', new_callable=AsyncMock) as mock_get:

        mock_fetch.return_value = mock_token
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_user_info
        mock_get.return_value = mock_resp

        response = await client.get("/auth/github/callback?code=gh_code", cookies=cookies, follow_redirects=False)

        # 4. Verify Redirect to Dashboard (Logic Fixed)
        assert response.status_code == 303
        assert response.headers["location"] == "/dashboard"

        # 5. Verify User Updated
        db_session.refresh(user)
        assert user.github_id == "999"
        assert user.avatar_url == "http://avatar.url/gh.jpg"

@pytest.mark.asyncio
async def test_github_conflict_flow(client, db_session):
    # 1. Create User A (Has GH ID 888)
    user_a = User(name="User A", email="a@example.com", hashed_password="pw", github_id="888")
    db_session.add(user_a)

    # 2. Create User B (LinkedIn only, Logged in)
    user_b = User(name="User B", email="b@example.com", hashed_password="pw", linkedin_id="L222")
    db_session.add(user_b)
    db_session.commit()

    # Login as B
    cookies = create_auth_cookie(user_b.id, user_b.email)

    # 3. Simulate GitHub Callback with ID 888
    mock_token = {'access_token': 'fake_gh_token', 'token_type': 'bearer'}
    mock_user_info = { 'id': 888, 'login': 'stolen', 'email': 'stolen@example.com' }

    with patch('app.routes.social.oauth.github.fetch_access_token', new_callable=AsyncMock) as mock_fetch, \
         patch('app.routes.social.oauth.github.get', new_callable=AsyncMock) as mock_get:

        mock_fetch.return_value = mock_token
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_user_info
        mock_get.return_value = mock_resp

        response = await client.get("/auth/github/callback?code=gh_code", cookies=cookies, follow_redirects=False)

        # 4. Verify Redirect to Error
        assert response.status_code == 302
        assert "/onboarding/connect-github?error=github_taken" in response.headers["location"]

@pytest.mark.asyncio
async def test_dashboard_protection(client, db_session):
    # 1. Create Incomplete User
    user = User(name="Incomplete", email="i@e.com", hashed_password="pw", linkedin_id="L1", is_profile_completed=False)
    db_session.add(user)
    db_session.commit()

    cookies = create_auth_cookie(user.id, user.email)

    # 2. Access Dashboard
    response = await client.get("/dashboard", cookies=cookies, follow_redirects=False)

    # 3. Verify Redirect (Should go to connect-github as he has linkedin but no github)
    assert response.status_code == 303
    assert response.headers["location"] == "/onboarding/connect-github"

    # 4. Update user to have github_id but incomplete profile
    # Use update to avoid session detachment issues in tests
    db_session.query(User).filter(User.id == user.id).update({"github_id": "G1"})
    db_session.commit()

    response = await client.get("/dashboard", cookies=cookies, follow_redirects=False)
    assert response.status_code == 200 # Now allowed (Logic Fixed)

    # 5. Complete profile
    db_session.query(User).filter(User.id == user.id).update({"is_profile_completed": True})
    db_session.commit()

    response = await client.get("/dashboard", cookies=cookies, follow_redirects=False)
    assert response.status_code == 200 # Now allowed

@pytest.mark.asyncio
async def test_career_protection(client, db_session):
    # 1. Create Incomplete User
    user = User(name="Incomplete", email="c@e.com", hashed_password="pw", linkedin_id="L1", is_profile_completed=False)
    db_session.add(user)
    db_session.commit()

    cookies = create_auth_cookie(user.id, user.email)

    # 2. POST /analyze-resume
    response = await client.post(
        "/career/analyze-resume",
        data={"resume_text": "foo"},
        cookies=cookies,
        follow_redirects=False
    )

    # 3. Verify Redirect
    assert response.status_code == 303
    assert response.headers["location"] == "/onboarding/connect-github"

@pytest.mark.asyncio
async def test_navigation_leak(client, db_session):
    # 1. Incomplete User (Has LinkedIn, no GitHub)
    user = User(
        name="NavCheck", email="n@e.com", hashed_password="pw",
        linkedin_id="L1", is_profile_completed=False
    )
    db_session.add(user)
    db_session.commit()

    cookies = create_auth_cookie(user.id, user.email)

    # 2. Access /onboarding/connect-github
    response = await client.get("/onboarding/connect-github", cookies=cookies)

    assert response.status_code == 200
    html = response.text

    # 3. Assert "Dashboard" link is NOT present
    assert 'href="/dashboard"' not in html

    # 4. Assert "Logout" link IS present
    assert 'href="/logout"' in html

    # 5. Complete profile (artificially set True to test template)
    db_session.query(User).filter(User.id == user.id).update({"is_profile_completed": True, "github_id": "G1"})
    db_session.commit()

    response = await client.get("/onboarding/connect-github", cookies=cookies, follow_redirects=False)

    # If github_id is set, it redirects to dashboard
    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard"
