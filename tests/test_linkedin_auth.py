import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch, AsyncMock, MagicMock
import os

# Ensure environment variables are set before importing app/routes
os.environ["LINKEDIN_CLIENT_ID"] = "test_client_id"
os.environ["LINKEDIN_CLIENT_SECRET"] = "test_client_secret"
os.environ["GITHUB_CLIENT_ID"] = "test_github_id"
os.environ["GITHUB_CLIENT_SECRET"] = "test_github_secret"
os.environ["SESSION_SECRET_KEY"] = "super-secret-key"

from app.main import app
from app.db.base import Base
from app.db.models.user import User
from app.db.session import get_db

# Setup Test DB
DB_FILE = "./test_linkedin.db"
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_FILE}"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="module")
def db_engine():
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)

@pytest.fixture(scope="function")
def db(db_engine):
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    # Patch get_db
    app.dependency_overrides[get_db] = lambda: session

    # Patch SessionLocal in AuthMiddleware (CRITICAL for session handling)
    original_close = session.close
    session.close = lambda: None

    with patch("app.middleware.auth.SessionLocal", lambda: session):
        yield session

    session.close = original_close
    session.close()
    transaction.rollback()
    connection.close()
    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
def client(db):
    with TestClient(app) as c:
        yield c

@pytest.mark.asyncio
async def test_linkedin_callback_missing_nonce_handled(client, db):
    """
    Test that the LinkedIn callback specifically relaxes the nonce requirement
    and successfully transitions to the GitHub onboarding step for a new user.
    """

    # 1. Mock the OAuth Object
    # We mock 'app.routes.social.oauth.linkedin'
    # authorize_access_token should be an AsyncMock
    # userinfo should be an AsyncMock

    mock_token = {
        "access_token": "fake_token",
        "token_type": "bearer",
        "expires_in": 3600,
        "id_token": "fake_id_token_without_nonce"
    }

    mock_user_info = {
        "sub": "linkedin_12345",
        "email": "testuser@example.com",
        "given_name": "Test",
        "family_name": "User",
        "picture": "http://example.com/avatar.jpg"
    }

    with patch("app.routes.social.oauth.linkedin.authorize_access_token", new_callable=AsyncMock) as mock_auth_token, \
         patch("app.routes.social.oauth.linkedin.userinfo", new_callable=AsyncMock) as mock_userinfo:

        mock_auth_token.return_value = mock_token
        mock_userinfo.return_value = mock_user_info

        # Act: Call the callback
        response = client.get("/auth/linkedin/callback", follow_redirects=False)

        # Assert 1: authorize_access_token was called with claims_options={'nonce': {'required': False}}
        args, kwargs = mock_auth_token.call_args

        # Verify claims_options is passed and nonce is not required
        assert "claims_options" in kwargs
        assert kwargs["claims_options"]["nonce"]["required"] is False

        # Assert 2: Flow Integrity - Redirects to Onboarding (since user has no GitHub)
        assert response.status_code == 303
        assert response.headers["location"] == "/onboarding/connect-github"

        # Verify user was created
        user = db.query(User).filter_by(email="testuser@example.com").first()
        assert user is not None
        assert user.linkedin_id == "linkedin_12345"
        assert user.github_id is None
        assert user.terms_accepted is True # Zero Touch


@pytest.mark.asyncio
async def test_linkedin_callback_zero_touch_flow(client, db):
    """
    Test that if a user already has GitHub connected (via prior logic),
    they are redirected straight to Dashboard.
    """

    # Pre-create user with LinkedIn AND GitHub
    user = User(
        email="existing@example.com",
        name="Existing User",
        linkedin_id="linkedin_999",
        github_id="github_888",
        hashed_password="hashed_secret",
        terms_accepted=True
    )
    db.add(user)
    db.commit()

    mock_token = {"access_token": "fake", "id_token": "fake_id"}
    mock_user_info = {
        "sub": "linkedin_999",
        "email": "existing@example.com",
        "name": "Existing User"
    }

    with patch("app.routes.social.oauth.linkedin.authorize_access_token", new_callable=AsyncMock) as mock_auth_token, \
         patch("app.routes.social.oauth.linkedin.userinfo", new_callable=AsyncMock) as mock_userinfo:

        mock_auth_token.return_value = mock_token
        mock_userinfo.return_value = mock_user_info

        # Act
        response = client.get("/auth/linkedin/callback", follow_redirects=False)

        # Assert: Redirect to Dashboard (Zero Touch)
        assert response.status_code == 303
        assert response.headers["location"] == "/dashboard"

        # Verify args again just to be sure
        _, kwargs = mock_auth_token.call_args
        assert kwargs["claims_options"]["nonce"]["required"] is False

@pytest.mark.asyncio
async def test_linkedin_callback_security_state_validation(client, db):
    """
    Test that state validation is still implicit (we are using authorize_access_token).
    We can't easily fail the state check with TestClient + Mock unless we simulate a raising exception from authorize_access_token.
    This test verifies that we handle exceptions gracefully (redirect to login?error=...).
    """

    with patch("app.routes.social.oauth.linkedin.authorize_access_token", new_callable=AsyncMock) as mock_auth_token:
        # Simulate Authlib raising MismatchingStateError or similar
        mock_auth_token.side_effect = Exception("MismatchingStateError")

        response = client.get("/auth/linkedin/callback", follow_redirects=False)

        # Expect redirect to login with error
        # In social.py: return RedirectResponse("/login?error=linkedin_failed")
        assert response.status_code == 307 or response.status_code == 303
        assert "/login?error=linkedin_failed" in response.headers["location"]
