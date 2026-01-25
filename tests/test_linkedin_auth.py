import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from authlib.jose.errors import MissingClaimError
from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.db.models.user import User

# --- Test DB Setup ---
# Use in-memory SQLite with StaticPool to share connection across threads/sessions
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="module")
def db_engine():
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db(db_engine):
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    app.dependency_overrides[get_db] = lambda: session

    # Patch SessionLocal for AuthMiddleware and other usages
    with patch("app.middleware.auth.SessionLocal", lambda: session):
        yield session

    session.close()
    transaction.rollback()
    connection.close()

    # Cleanup dependency overrides to prevent pollution
    app.dependency_overrides.pop(get_db, None)

@pytest.fixture(scope="function")
def client(db):
    with TestClient(app) as c:
        yield c

# --- Mocks ---

@pytest.fixture
def mock_oauth():
    # Patch the global oauth object in social.py
    with patch("app.routes.social.oauth") as mock:
        # Create an AsyncMock for authorize_access_token because it's awaited
        mock.linkedin.authorize_access_token = AsyncMock()
        mock.linkedin.userinfo = AsyncMock()
        yield mock

# --- Tests ---

def test_linkedin_callback_missing_nonce_handled(client, mock_oauth, db):
    """
    Verifies that authorize_access_token is called with nonce verification disabled.
    If not disabled, the mock raises MissingClaimError, simulating failure.
    Also verifies flow for NEW user -> Connect GitHub.
    """

    # 1. Define the side effect to simulate 'MissingClaimError' if nonce is not relaxed
    async def authorize_side_effect(request, **kwargs):
        claims_options = kwargs.get('claims_options', {})
        nonce_options = claims_options.get('nonce', {})

        # This asserts that the fix IS present.
        # If 'required': False is not passed, we raise the error that production is seeing.
        if nonce_options.get('required') is not False:
            raise MissingClaimError("nonce")

        return {'access_token': 'test_token', 'id_token': 'test_id_token'}

    mock_oauth.linkedin.authorize_access_token.side_effect = authorize_side_effect

    # 2. Mock User Info (New User)
    mock_oauth.linkedin.userinfo.return_value = {
        'sub': 'linkedin_123',
        'email': 'newuser@example.com',
        'name': 'New User',
        'picture': 'http://avatar.url'
    }

    # 3. Call the callback endpoint
    response = client.get("/auth/linkedin/callback?code=fake_code&state=fake_state", follow_redirects=False)

    # 4. Verification

    # Verify authorize_access_token was called
    assert mock_oauth.linkedin.authorize_access_token.called

    # Verify claims_options was correctly passed (redundant with side_effect but good for clarity)
    call_args = mock_oauth.linkedin.authorize_access_token.call_args
    assert call_args.kwargs['claims_options']['nonce']['required'] is False

    # Verify Redirect to Onboarding (Zero-Touch: New user needs GitHub)
    assert response.status_code == 303
    assert response.headers["location"] == "/onboarding/connect-github"

    # Verify User created in DB
    user = db.query(User).filter(User.email == "newuser@example.com").first()
    assert user is not None
    assert user.linkedin_id == "linkedin_123"
    assert user.github_id is None
    assert user.terms_accepted is True # Zero Touch implicit consent


def test_linkedin_callback_existing_user_flow(client, mock_oauth, db):
    """
    Verifies flow for EXISTING user with GitHub -> Dashboard.
    (Zero-Touch Chain integrity)
    """
    # 1. Setup Mock (Success)
    mock_oauth.linkedin.authorize_access_token.return_value = {'access_token': 't', 'id_token': 'i'}

    # 2. Setup Existing User with GitHub
    existing_user = User(
        email="existing@example.com",
        name="Existing User",
        linkedin_id="linkedin_456",
        github_id="github_789",
        hashed_password="hash",
        terms_accepted=True
    )
    db.add(existing_user)
    db.commit()

    # 3. Mock User Info matching existing user
    mock_oauth.linkedin.userinfo.return_value = {
        'sub': 'linkedin_456',
        'email': 'existing@example.com',
        'name': 'Existing User',
        'picture': 'http://avatar.url'
    }

    # 4. Call Callback
    response = client.get("/auth/linkedin/callback?code=fake&state=fake", follow_redirects=False)

    # 5. Verify Redirect to Dashboard
    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard"


def test_linkedin_callback_security_checks(client, mock_oauth):
    """
    Verifies that the callback endpoint calls authorize_access_token with the request object,
    which is essential for Authlib's internal state (CSRF) validation.
    """
    mock_oauth.linkedin.authorize_access_token.return_value = {'access_token': 't', 'id_token': 'i'}
    mock_oauth.linkedin.userinfo.return_value = {'sub': 'u', 'email': 'e@e.com'}

    client.get("/auth/linkedin/callback?code=c&state=s", follow_redirects=False)

    # Verify first argument was the request object
    call_args = mock_oauth.linkedin.authorize_access_token.call_args
    # call_args[0] is args tuple. First arg should be request.
    arg_request = call_args[0][0]
    assert hasattr(arg_request, "query_params")
    assert arg_request.query_params["state"] == "s"
