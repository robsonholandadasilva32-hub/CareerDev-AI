import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.declarative import Base
from app.db.models.user import User
from app.db.models.security import UserSession
# Import other models to ensure Metadata is populated
from app.db.models.career import CareerProfile, LearningPlan
from app.db.models.gamification import UserBadge
from app.db.session import get_db
from app.core.jwt import create_access_token

# Setup Test DB
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
    # Override get_db
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    # Patch Middleware SessionLocal to use our test session factory
    # Note: Middleware calls SessionLocal(), so we need to return a session instance or the factory?
    # app.middleware.auth.SessionLocal is the class/factory.
    # So return_value should be the factory? No, if called as class(), return_value is the instance.
    # Wait, SessionLocal() returns a session.
    # So if we patch 'app.middleware.auth.SessionLocal', its return_value (when called) should be a session.
    # We'll use TestingSessionLocal() which creates a new session connected to our engine.

    with patch("app.middleware.auth.SessionLocal", side_effect=TestingSessionLocal) as mock_session_local:
        with TestClient(app) as c:
            yield c

    app.dependency_overrides.clear()

def test_career_analytics_performance(client, db_session):
    # 1. Setup User
    user = User(
        name="Perf User",
        email="perf@example.com",
        hashed_password="hash",
        is_profile_completed=True,
        linkedin_id="li_perf",
        github_id="gh_perf",
        is_premium=True,
        subscription_status="active"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

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

    # Define listener
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        nonlocal query_count
        # print(f"Query: {statement}") # Debug
        query_count += 1

    # Attach listener to the test engine
    event.listen(engine, "before_cursor_execute", before_cursor_execute)

    try:
        response = client.get("/career/analytics")
    finally:
        event.remove(engine, "before_cursor_execute", before_cursor_execute)

    # 5. Verify Response
    assert response.status_code == 200, f"Response: {response.text}"

    print(f"\nQUERY COUNT: {query_count}")

    # 6. Assertions
    # Baseline: 3 queries (Session, User(Middleware), User(Route))
    # Optimized goal: 2 queries
    # Asserting 3 first to confirm baseline
    assert query_count == 2
