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
os.environ.setdefault("SECRET_KEY", "test_secret_key")

from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.declarative import Base
from app.db.session import get_db
# Ensure all models are loaded for relationships
from app.db.models.user import User
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

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")

@pytest.mark.asyncio
async def test_linkedin_callback_success(client, db_session):
    # Ensure linkedin client is registered
    from app.routes.social import oauth
    if 'linkedin' not in oauth._registry:
         oauth.register(
            name='linkedin',
            client_id='mock_id',
            client_secret='mock_secret',
            server_metadata_url='https://www.linkedin.com/oauth/.well-known/openid-configuration',
            client_kwargs={'scope': 'openid profile email'}
        )

    # Mock Token Response and User Info
    mock_token = {'access_token': 'fake_token', 'token_type': 'bearer'}

    mock_user_info = {
        'sub': 'linkedin-12345',
        'email': 'testuser@linkedin.com',
        'name': 'Test User',
        'picture': 'http://avatar.url/pic.jpg',
        'given_name': 'Test',
        'family_name': 'User'
    }

    # Patch fetch_access_token (Bypassing authorize_access_token wrapper)
    # AND userinfo
    # AND hash_password to avoid bcrypt issues
    with patch('app.routes.social.oauth.linkedin.fetch_access_token', new_callable=AsyncMock) as mock_fetch, \
         patch('app.routes.social.oauth.linkedin.userinfo', new_callable=AsyncMock) as mock_userinfo, \
         patch('app.routes.social.hash_password', return_value="mock_hashed_pwd") as mock_hash:

        mock_fetch.return_value = mock_token
        mock_userinfo.return_value = mock_user_info

        # Act
        response = await client.get("/auth/linkedin/callback?code=123&state=abc", follow_redirects=False)

        # Assert
        assert response.status_code == 302
        # Updated to expect redirection to GitHub connection step (Progressive Onboarding)
        assert response.headers["location"] == "/onboarding/connect-github"

        # Verify fetch_access_token was called correctly
        mock_fetch.assert_called_once()
        call_kwargs = mock_fetch.call_args.kwargs

        # The critical check: verify we are passing redirect_uri explicitly as a string
        assert 'redirect_uri' in call_kwargs
        assert isinstance(call_kwargs['redirect_uri'], str)

        # Since we are not in production env during tests, it stays http://
        assert call_kwargs['redirect_uri'].startswith("http://test/auth/linkedin/callback")

        # Verify grant_type and code
        assert call_kwargs.get('grant_type') == 'authorization_code'
        assert call_kwargs.get('code') == '123'

        # Verify user created in DB
        from app.db.crud.users import get_user_by_email
        user = get_user_by_email(db_session, "testuser@linkedin.com")
        assert user is not None
        assert user.linkedin_id == "linkedin-12345"

@pytest.mark.asyncio
async def test_github_callback_success(client, db_session):
    # Ensure github client is registered
    from app.routes.social import oauth
    if 'github' not in oauth._registry:
         oauth.register(
            name='github',
            client_id='mock_gh_id',
            client_secret='mock_gh_secret',
            access_token_url='https://github.com/login/oauth/access_token',
            authorize_url='https://github.com/login/oauth/authorize',
            api_base_url='https://api.github.com/',
            client_kwargs={'scope': 'user:email'},
        )

    # Mock Token Response and User Info
    mock_token = {'access_token': 'fake_gh_token', 'token_type': 'bearer'}

    mock_user_info = {
        'id': 98765,
        'login': 'githubuser',
        'email': 'github@example.com',
        'name': 'GitHub User',
        'avatar_url': 'http://avatar.url/gh.jpg'
    }

    # Patch fetch_access_token and get (for user info)
    # AND hash_password
    with patch('app.routes.social.oauth.github.fetch_access_token', new_callable=AsyncMock) as mock_fetch, \
         patch('app.routes.social.oauth.github.get', new_callable=AsyncMock) as mock_get, \
         patch('app.routes.social.hash_password', return_value="mock_hashed_pwd") as mock_hash:

        mock_fetch.return_value = mock_token

        # mock_get is called for 'user' and potentially 'user/emails'
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_user_info
        mock_get.return_value = mock_resp

        # Act
        response = await client.get("/auth/github/callback?code=gh_code&state=gh_state", follow_redirects=False)

        # Assert
        assert response.status_code == 302
        # Updated to expect redirection to LinkedIn login if LinkedIn is missing
        assert response.headers["location"] == "/login/linkedin"

        # Verify fetch_access_token was called correctly
        mock_fetch.assert_called_once()
        call_kwargs = mock_fetch.call_args.kwargs

        # The critical check: verify we are passing redirect_uri explicitly as a string
        assert 'redirect_uri' in call_kwargs
        assert isinstance(call_kwargs['redirect_uri'], str)
        # Not production, so http://
        assert call_kwargs['redirect_uri'].startswith("http://test/auth/github/callback")

        # Verify grant_type and code
        assert call_kwargs.get('grant_type') == 'authorization_code'
        assert call_kwargs.get('code') == 'gh_code'

        # Verify user created in DB
        from app.db.crud.users import get_user_by_email
        user = get_user_by_email(db_session, "github@example.com")
        assert user is not None
        assert user.github_id == "98765"

@pytest.mark.asyncio
async def test_github_connect_existing_user(client, db_session):
    # 1. Create existing user (as if logged in via LinkedIn)
    existing_user = User(
        email="linkeduser@example.com",
        name="LinkedIn User",
        hashed_password="fake_hash",
        linkedin_id="linkedin-original-123",
        # is_active removed as it's not a column
        email_verified=True,
        is_profile_completed=False
    )
    db_session.add(existing_user)
    db_session.commit()
    db_session.refresh(existing_user)

    # 2. Generate Auth Token
    token_data = {
        "sub": str(existing_user.id),
        "email": existing_user.email
    }
    access_token = create_access_token(token_data)

    # 3. Set Cookie
    client.cookies.set("access_token", access_token)

    # 4. Mock GitHub Response
    mock_token = {'access_token': 'fake_gh_token_link', 'token_type': 'bearer'}
    mock_user_info = {
        'id': 55555,
        'login': 'linkedgithub',
        'email': 'linkedgithub@example.com',
        'name': 'Linked GitHub User',
        'avatar_url': 'http://avatar.url/gh_link.jpg'
    }

    # Create session proxy to prevent middleware from closing it
    session_proxy = MagicMock(wraps=db_session)
    session_proxy.close = MagicMock()

    with patch('app.routes.social.oauth.github.fetch_access_token', new_callable=AsyncMock) as mock_fetch, \
         patch('app.routes.social.oauth.github.get', new_callable=AsyncMock) as mock_get, \
         patch("app.middleware.auth.SessionLocal", return_value=session_proxy):

        mock_fetch.return_value = mock_token

        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_user_info
        mock_get.return_value = mock_resp

        # 5. Act
        response = await client.get("/auth/github/callback?code=gh_link_code", follow_redirects=False)

        # 6. Assert
        assert response.status_code == 302
        # Since profile is not completed, it should go to complete profile
        assert response.headers["location"] == "/onboarding/complete-profile"

        # Verify DB update
        # Since session_proxy prevents close, db_session is still valid?
        # db_session.refresh should work if transaction was committed.
        # AuthMiddleware commits? No, it just reads.
        # auth_github_callback commits.
        # Since we use the SAME session instance (db_session via proxy), the commit in route affects db_session.
        db_session.refresh(existing_user)
        assert existing_user.github_id == "55555"
        assert existing_user.linkedin_id == "linkedin-original-123"
