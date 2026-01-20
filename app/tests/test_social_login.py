import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import AsyncMock, patch

from app.main import app
from app.db.declarative import Base
# Import models to ensure they are registered
from app.db.models.user import User
from app.db.models.gamification import UserBadge
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
    # Ensure linkedin client is registered (mock environment usually lacks credentials)
    from app.routes.social import oauth
    if 'linkedin' not in oauth._registry:
         oauth.register(
            name='linkedin',
            client_id='mock_id',
            client_secret='mock_secret',
            server_metadata_url='https://www.linkedin.com/oauth/.well-known/openid-configuration',
            client_kwargs={'scope': 'openid profile email'}
        )

    # Mock Token Response
    mock_token = {
        'userinfo': {
            'sub': 'linkedin-12345',
            'email': 'testuser@linkedin.com',
            'name': 'Test User',
            'picture': 'http://avatar.url/pic.jpg',
            'given_name': 'Test',
            'family_name': 'User'
        }
    }

    # Patch the authorize_access_token method on the oauth.linkedin object
    with patch('app.routes.social.oauth.linkedin.authorize_access_token', new_callable=AsyncMock) as mock_auth:
        mock_auth.return_value = mock_token

        # Act
        response = await client.get("/auth/linkedin/callback?code=123&state=abc", follow_redirects=False)

        # Assert
        assert response.status_code == 302
        assert response.headers["location"] == "/dashboard"
        assert "access_token" in response.cookies

        # Verify user created in DB
        from app.db.crud.users import get_user_by_email
        user = get_user_by_email(db_session, "testuser@linkedin.com")
        assert user is not None
        assert user.linkedin_id == "linkedin-12345"
