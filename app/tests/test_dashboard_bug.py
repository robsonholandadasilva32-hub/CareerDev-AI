import pytest
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.models.user import User
from app.core.jwt import create_access_token
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db

# Setup Test DB with StaticPool for in-memory SQLite to work across threads
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Ensure tables exist
Base.metadata.create_all(bind=engine)

@pytest.fixture
def db_session():
    # Use the TestingSessionLocal
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture
def client(db_session):
    app.dependency_overrides = {}

    # Override get_db to use our test session
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db

    # Patch Middleware SessionLocal to use our test session factory
    with patch("app.middleware.auth.SessionLocal", side_effect=TestingSessionLocal):
        transport = ASGITransport(app=app)
        yield AsyncClient(transport=transport, base_url="http://test")

    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_dashboard_rendering_error(client, db_session):
    # 1. Create a test user
    email = "dashboard_test@example.com"
    # Cleanup if exists
    existing = db_session.query(User).filter(User.email == email).first()
    if existing:
        db_session.query(User).filter(User.email == email).delete()
        db_session.commit()

    user = User(
        email=email,
        name="Dashboard Test User",
        hashed_password=hash_password("password123"),
        github_id="test_gh_id",  # Bypass onboarding check
        linkedin_id="test_li_id" # Bypass onboarding check
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    try:
        # 2. Generate Token
        access_token = create_access_token({"sub": str(user.id)})

        # 3. Request Dashboard
        cookies = {"access_token": access_token}

        # This should fail if 'user' is missing in template context
        response = await client.get("/dashboard", cookies=cookies)

        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}. Content: {response.text[:200]}..."
        assert "Dashboard" in response.text or "CareerDev AI" in response.text

    finally:
        # Clean up
        db_session.query(User).filter(User.email == email).delete()
        db_session.commit()
