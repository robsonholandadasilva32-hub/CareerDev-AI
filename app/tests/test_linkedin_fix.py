import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import AsyncMock, patch, ANY

from app.main import app
from app.db.declarative import Base
from app.db.session import get_db

# Setup In-Memory DB
DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

@pytest.fixture(scope="function")
def db_session():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides = {}

@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")

@pytest.mark.asyncio
async def test_linkedin_callback_manual_code_extraction(client, db_session):
    # Ensure linkedin client is registered
    from app.routes.social import oauth
    # We need to ensure settings allow registration logic to run or manually register if not
    # However, in tests, app is already initialized.
    # But usually settings are mocked or empty in tests, so social routes might skip registration if we don't force it.
    if 'linkedin' not in oauth._registry:
         oauth.register(
            name='linkedin',
            client_id='mock_id',
            client_secret='mock_secret',
            server_metadata_url='https://www.linkedin.com/oauth/.well-known/openid-configuration',
            client_kwargs={'scope': 'openid profile email'}
        )

    # Mock Token and UserInfo
    mock_token = {'access_token': 'valid_token'}
    mock_user_info = {
        'sub': 'linkedin-new-fix',
        'email': 'fixed@linkedin.com',
        'name': 'Fixed User',
        'picture': 'http://pic.com'
    }

    # Patch fetch_access_token AND userinfo
    # Note: We patch on the oauth.linkedin instance which is created in app.routes.social
    with patch('app.routes.social.oauth.linkedin.fetch_access_token', new_callable=AsyncMock) as mock_fetch, \
         patch('app.routes.social.oauth.linkedin.userinfo', new_callable=AsyncMock) as mock_userinfo:

        mock_fetch.return_value = mock_token
        mock_userinfo.return_value = mock_user_info

        # Act: Call callback with a code
        test_code = "auth_code_123"
        response = await client.get(f"/auth/linkedin/callback?code={test_code}", follow_redirects=False)

        # Assert 1: fetch_access_token called with correct arguments
        mock_fetch.assert_called_once()
        call_args = mock_fetch.call_args

        # Check args/kwargs
        # Signature: fetch_access_token(request, grant_type=..., code=...)
        # request is first arg
        assert call_args[0][0] is not None # Request object

        kwargs = call_args[1]
        assert kwargs['grant_type'] == 'authorization_code'
        assert kwargs['code'] == test_code

        # CRITICAL: Verify redirect_uri is NOT present
        assert 'redirect_uri' not in kwargs

        # Assert 2: Flow completed (redirect to dashboard)
        assert response.status_code == 302
        assert response.headers["location"] == "/dashboard"

@pytest.mark.asyncio
async def test_linkedin_callback_missing_code(client):
     # Act: Call callback WITHOUT code
    response = await client.get("/auth/linkedin/callback", follow_redirects=False)

    # Assert: Redirect to error page
    assert response.status_code == 307
    assert response.headers["location"] == "/login?error=linkedin_failed"
