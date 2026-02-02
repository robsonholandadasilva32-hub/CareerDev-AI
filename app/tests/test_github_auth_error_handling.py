import os
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from authlib.integrations.base_client.errors import OAuthError

# 1. Set required environment variables BEFORE importing app.main
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test_secret_key"
os.environ["GITHUB_CLIENT_ID"] = "mock_gh_id"
os.environ["GITHUB_CLIENT_SECRET"] = "mock_gh_secret"
os.environ["OPENAI_API_KEY"] = "sk-mock-key" # Mock key to prevent startup error

from app.main import app
from app.core.jwt import create_access_token
from app.db.models.user import User
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker
from app.db.base_class import Base
from app.db.session import get_db

# Setup In-Memory DB
DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)

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

@pytest.mark.asyncio
async def test_github_callback_oauth_error_handling(db_session):
    # 1. Setup User and Auth
    user = User(
        email="test@example.com",
        hashed_password="hash",
        full_name="Test User",
        email_verified=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    token = create_access_token({"sub": str(user.id), "email": user.email})

    # 2. Setup Client
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        client.cookies.set("access_token", token)

        # 3. Mock OAuth Error
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

        # Patch SessionLocal in AuthMiddleware and OAuth fetch_access_token
        # We also need to mock session in route handler? No, override_get_db handles it.
        # But AuthMiddleware creates its own session using SessionLocal().

        with patch("app.middleware.auth.SessionLocal", return_value=db_session), \
             patch("app.routes.social.oauth.github.fetch_access_token", new_callable=AsyncMock) as mock_fetch:

            # Simulate the specific error requested
            error_instance = OAuthError(
                error='bad_verification_code',
                description='The code passed is incorrect or expired.',
                uri='http://docs.github.com'
            )
            mock_fetch.side_effect = error_instance

            # 4. Act
            # We follow redirects=False to check the immediate redirect response
            response = await client.get("/auth/github/callback?code=bad_code&state=xyz", follow_redirects=False)

            # 5. Assert
            print(f"DEBUG: Status: {response.status_code}")
            print(f"DEBUG: Location Header: {response.headers.get('location')}")

            # Redirect should happen
            assert response.status_code in [302, 303, 307]

            # Expected failure point: currently likely /login?error=github_failed
            # Goal: /login?error=github_code_expired
            assert "/login?error=github_code_expired" in response.headers["location"]
