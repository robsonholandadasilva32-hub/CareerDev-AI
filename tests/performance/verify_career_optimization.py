import sys
from unittest.mock import MagicMock

# Mock heavy dependencies before they are imported by app code
tf_mock = MagicMock()
sys.modules["tensorflow"] = tf_mock
sys.modules["tensorflow.keras"] = MagicMock()
sys.modules["tensorflow.keras.models"] = MagicMock()
sys.modules["tensorflow.keras.layers"] = MagicMock()
sys.modules["tensorflow.keras.callbacks"] = MagicMock()

sys.modules["mlflow"] = MagicMock()
sys.modules["openai"] = MagicMock()
sys.modules["pandas"] = MagicMock()

sklearn_mock = MagicMock()
sys.modules["sklearn"] = sklearn_mock
sys.modules["sklearn.linear_model"] = MagicMock()
sys.modules["sklearn.ensemble"] = MagicMock()
sys.modules["sklearn.preprocessing"] = MagicMock()
sys.modules["sklearn.model_selection"] = MagicMock()
sys.modules["sklearn.metrics"] = MagicMock()

sys.modules["joblib"] = MagicMock()
sys.modules["numpy"] = MagicMock()
sys.modules["sentry_sdk"] = MagicMock()

import os
# Set required env vars
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["OPENAI_API_KEY"] = "sk-test"
os.environ["AUTH_SECRET"] = "secret"
os.environ["GITHUB_CLIENT_ID"] = "gh-id"
os.environ["GITHUB_CLIENT_SECRET"] = "gh-secret"
os.environ["LINKEDIN_CLIENT_ID"] = "li-id"
os.environ["LINKEDIN_CLIENT_SECRET"] = "li-secret"

import asyncio
import time
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Now import app
from app.main import app
from app.db.base import Base
from app.db.models.user import User
from app.db.models.career import CareerProfile
from app.db.models.security import UserSession
from app.db.session import get_db
from app.core.jwt import create_access_token

# Setup In-Memory DB
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="module")
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session(setup_db):
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

async def monitor_event_loop(duration: float, interval: float = 0.01):
    """
    Monitors the event loop lag.
    Returns the maximum lag detected (in seconds).
    """
    start_time = time.time()
    max_lag = 0.0

    while time.time() - start_time < duration:
        loop_start = time.time()
        await asyncio.sleep(interval)
        loop_end = time.time()

        # Expected duration is 'interval'
        actual_duration = loop_end - loop_start
        lag = actual_duration - interval

        if lag > max_lag:
            max_lag = lag

    return max_lag

@pytest.mark.asyncio
async def test_linkedin_post_blocking(db_session):
    # 1. Setup Data
    user = User(
        full_name="Blocking Test User",
        email="blocking@example.com",
        hashed_password="hash",
        is_active=True,
        is_profile_completed=True # Skip onboarding checks
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Add Career Profile with data
    profile = CareerProfile(
        user_id=user.id,
        skills_snapshot={"Python": 90, "Rust": 80},
        target_role="Senior Engineer"
    )
    db_session.add(profile)

    # Add User Session for Auth
    session_id = "block_sid"
    user_session = UserSession(
        id=session_id,
        user_id=user.id,
        is_active=True,
        user_agent="test_ua"
    )
    db_session.add(user_session)
    db_session.commit()

    # 2. Mock Dependencies
    app.dependency_overrides[get_db] = lambda: db_session

    # Mock AuthMiddleware's SessionLocal to avoid creating new real connections
    with patch("app.middleware.auth.SessionLocal", side_effect=lambda: db_session):

        # Mock Chatbot Service to be fast and non-blocking
        with patch("app.routes.career.chatbot_service") as mock_chatbot:
            mock_chatbot.generate_linkedin_post = AsyncMock(return_value="Mocked Post Content")

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                token = create_access_token({"sub": str(user.id), "sid": session_id})
                cookies = {"access_token": token}

                # 3. Run Benchmark
                # Start the monitor task
                monitor_task = asyncio.create_task(monitor_event_loop(duration=2.0))

                # Fire multiple requests to stress the loop
                # We need enough requests to make sync I/O noticeable if it exists.
                start_req = time.time()
                for _ in range(50):
                    response = await ac.post("/career/api/generate-linkedin-post", cookies=cookies)
                    assert response.status_code == 200

                # Wait for monitor to finish (or cancel it if requests are done fast)
                max_lag = await monitor_task

                print(f"\nMax Event Loop Lag: {max_lag*1000:.2f}ms")

                # 4. Assert Performance
                # If blocking I/O occurs (sync DB access), lag will spike.
                # Threshold set to 100ms to account for test environment overhead while catching severe blocking.
                if max_lag > 0.10: # 100ms
                     pytest.fail(f"Event loop blocked significantly! Max lag: {max_lag*1000:.2f}ms")

    app.dependency_overrides.clear()
