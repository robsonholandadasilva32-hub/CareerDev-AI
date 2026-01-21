import os
import pytest
from unittest.mock import AsyncMock, patch

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

    # Patch fetch_access_token AND userinfo (NOT authorize_access_token)
    with patch('app.routes.social.oauth.linkedin.fetch_access_token', new_callable=AsyncMock) as mock_fetch, \
         patch('app.routes.social.oauth.linkedin.userinfo', new_callable=AsyncMock) as mock_userinfo:

        mock_fetch.return_value = mock_token
        mock_userinfo.return_value = mock_user_info

        # Act
        response = await client.get("/auth/linkedin/callback?code=123&state=abc", follow_redirects=False)

        # Assert
        assert response.status_code == 302
        assert response.headers["location"] == "/dashboard"

        # Verify fetch_access_token was called correctly
        mock_fetch.assert_called_once()
        call_kwargs = mock_fetch.call_args.kwargs

        # The critical check: verify we are manually passing grant_type='authorization_code' and the code
        assert call_kwargs.get('grant_type') == 'authorization_code'
        assert call_kwargs.get('code') == '123'

        # Verify we are NOT passing redirect_uri (Authlib pulls it from session, manual passing causes TypeError)
        assert 'redirect_uri' not in call_kwargs

        # Verify user created in DB
        from app.db.crud.users import get_user_by_email
        user = get_user_by_email(db_session, "testuser@linkedin.com")
        assert user is not None
        assert user.linkedin_id == "linkedin-12345"
