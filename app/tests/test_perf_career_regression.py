import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import os

# Set ENV vars before imports to ensure consistent test environment
os.environ["OPENAI_API_KEY"] = "sk-test"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.main import app
from app.db.base import Base
from app.db.models.user import User
from app.db.models.security import UserSession
from app.db.models.career import CareerProfile
from app.db.session import get_db
from app.core.jwt import create_access_token
from app.ai.chatbot import chatbot_service

# Setup Test DB with StaticPool for in-memory persistence across threads
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="module")
def init_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session(init_db):
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    # Mock Chatbot Service to avoid external API calls
    with patch.object(chatbot_service, 'generate_linkedin_post', new_callable=AsyncMock) as mock_method:
        mock_method.return_value = "Test Post"

        # Patch Middleware SessionLocal to use our testing session
        with patch("app.middleware.auth.SessionLocal", side_effect=TestingSessionLocal):
            with TestClient(app) as c:
                yield c

    app.dependency_overrides.clear()

def test_career_profile_no_nplusone(client, db_session):
    """
    Regression test to ensure accessing the career profile for LinkedIn post generation
    does not trigger N+1 queries (lazy loading) inside the route.

    Expected Queries:
    1. AuthMiddleware: Fetch Session
    2. AuthMiddleware: Fetch User (Auth context)
    3. Route Dependency: Fetch User + Joined CareerProfile (and Badges)

    Total: 3 Queries.
    If joinedload is missing, we would see a 4th query for the profile access.
    """
    # 1. Setup User
    user = User(
        full_name="Perf User",
        email="perf@example.com",
        hashed_password="hash",
        linkedin_profile_url="li_perf",
        github_username="gh_perf",
        is_profile_completed=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Add Career Profile
    profile = CareerProfile(user_id=user.id, skills_snapshot={"Python": 90})
    db_session.add(profile)
    db_session.commit()

    # 2. Setup Session
    session_id = "perf_sid"
    user_session = UserSession(
        id=session_id,
        user_id=user.id,
        is_active=True,
        user_agent="test_ua"
    )
    db_session.add(user_session)
    db_session.commit()

    # 3. Auth Token
    token = create_access_token({"sub": str(user.id), "sid": session_id})
    client.cookies.set("access_token", token)

    # 4. Count Queries
    query_count = 0

    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        nonlocal query_count
        # print(f"QUERY: {statement}")
        query_count += 1

    event.listen(engine, "before_cursor_execute", before_cursor_execute)

    try:
        response = client.post("/career/api/generate-linkedin-post")
    finally:
        event.remove(engine, "before_cursor_execute", before_cursor_execute)

    assert response.status_code == 200, f"Response: {response.text}"

    # Assert query count is strictly 3.
    # If optimization regression occurs, this will likely become 4.
    assert query_count == 3, f"Expected 3 queries (AuthSession, AuthUser, UserWithProfile). Found {query_count}. Possible N+1 regression."
