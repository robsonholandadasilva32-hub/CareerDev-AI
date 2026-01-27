import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.main import app
from app.db.session import SessionLocal, engine
from app.db.models.user import User
from app.db.models.gamification import Badge, UserBadge
from app.core.jwt import create_access_token
from app.core.security import hash_password
from app.db.base import Base

# Ensure tables exist
Base.metadata.create_all(bind=engine)

@pytest.fixture
def db_session():
    """Fixture to create a new database session for each test."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture
def client():
    """Fixture to create a test client."""
    app.dependency_overrides = {}  # Reset overrides
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")

class QueryCounter:
    """A context manager to count SQLAlchemy queries."""
    def __init__(self, db_engine):
        self.engine = db_engine
        self.count = 0

    def __enter__(self):
        event.listen(self.engine, "before_cursor_execute", self.callback)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        event.remove(self.engine, "before_cursor_execute", self.callback)

    def callback(self, conn, cursor, statement, parameters, context, executemany):
        self.count += 1

@pytest.fixture(scope="function")
def test_user_with_badges(db_session: Session):
    """Fixture to create a user with several badges."""
    # Clean up previous data
    db_session.query(UserBadge).delete()
    db_session.query(Badge).delete()
    db_session.query(User).filter(User.email == "nplus1@example.com").delete()
    db_session.commit()

    # Create User
    user = User(
        email="nplus1@example.com",
        name="N+1 Test User",
        hashed_password=hash_password("password"),
        is_premium=True,
        github_id="test_gh_id",
        linkedin_id="test_li_id",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Create Badges
    badges = []
    for i in range(5):
        badge = Badge(
            slug=f"test-badge-{i}",
            name=f"Test Badge {i}",
            description=f"Description for badge {i}",
            icon="🏆",
        )
        badges.append(badge)
    db_session.add_all(badges)
    db_session.commit()

    # Assign Badges to User
    for badge in badges:
        db_session.refresh(badge)
        user_badge = UserBadge(user_id=user.id, badge_id=badge.id)
        db_session.add(user_badge)
    db_session.commit()

    db_session.refresh(user)
    return user

@pytest.mark.asyncio
async def test_dashboard_avoids_nplus1(client: AsyncClient, test_user_with_badges: User):
    """
    Verify that the dashboard does not trigger N+1 queries when loading user badges.
    """
    user = test_user_with_badges
    access_token = create_access_token({"sub": str(user.id)})
    cookies = {"access_token": access_token}

    with QueryCounter(engine) as counter:
        response = await client.get("/dashboard", cookies=cookies, headers={"X-Forwarded-Proto": "https"})
        assert response.status_code == 200
        # The key assertion: check the number of queries.
        # This number might need adjustment based on other operations in the endpoint,
        # but it should be a small, constant number.
        # 1. Get User + Badges (1 query due to joinedload)
        # 2. Career Profile check/creation (potentially 1-2 queries)
        # 3. Learning Plan generation (potentially 1-2 queries)
        # A safe upper bound would be 5. The crucial part is that it's not 1 (user) + 5 (badges) = 6+.
        assert counter.count < 5, f"Too many queries ({counter.count}), N+1 problem likely exists."
