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
from app.db.declarative import Base
from app.db.session import get_db

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
    with patch('app.routes.social.oauth.linkedin.fetch_access_token', new_callable=AsyncMock) as mock_fetch, \
         patch('app.routes.social.oauth.linkedin.userinfo', new_callable=AsyncMock) as mock_userinfo:

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
    with patch('app.routes.social.oauth.github.fetch_access_token', new_callable=AsyncMock) as mock_fetch, \
         patch('app.routes.social.oauth.github.get', new_callable=AsyncMock) as mock_get:

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
