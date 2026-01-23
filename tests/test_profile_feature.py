import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure models are imported before creating tables
from app.db.declarative import Base
from app.db.models.user import User
from app.db.models.security import UserSession, AuditLog
from app.db.models.gamification import UserBadge, Badge
from app.db.models.career import CareerProfile, LearningPlan

from app.main import app
from app.db.session import get_db
from app.routes.dashboard import get_current_user_secure

# Setup In-Memory DB
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# Create tables
Base.metadata.create_all(bind=engine)

client = TestClient(app)

@pytest.fixture
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def test_user(db_session):
    user = User(
        email="test_profile@example.com",
        name="Profile Tester",
        hashed_password="hashed_password",
        is_profile_completed=True,
        github_id="gh_123",
        linkedin_id="li_123"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

def test_profile_update(db_session, test_user):
    # Override dependencies
    app.dependency_overrides[get_db] = override_get_db

    # We need to ensure the override returns the SAME user object attached to the current session
    # OR relies on the session provided by override_get_db
    def override_get_user():
        db = TestingSessionLocal()
        try:
             return db.query(User).filter(User.id == test_user.id).first()
        finally:
            db.close()

    # Actually, simpler: just return the ID and let the route refetch if it does?
    # No, the dependency returns the User object.
    # The issue is that the route uses `db: Session = Depends(get_db)`.
    # And `user: User = Depends(get_current_user_secure)`
    # `get_current_user_secure` usually uses `request.state.user`.

    # For the test, we can mock `get_current_user_secure` to return our test_user.
    # But we must ensure it's attached to the `db` session used in the route, or use `db.merge(user)`.
    # Since `override_get_db` creates a new session each time, `test_user` (from fixture) might be detached or from a different session.

    # Strategy:
    # The route does: `user.name = name`.
    # If `user` is detached, this is fine, but `db.commit()` needs the user to be in `db`.
    # The route uses `db` from dependency.
    # If we override `get_current_user_secure`, we should return a user that is valid.

    app.dependency_overrides[get_current_user_secure] = lambda: test_user

    # However, `test_user` comes from `db_session` fixture.
    # `override_get_db` creates a NEW session.
    # So `db.commit()` in the route will commit the NEW session.
    # But `user` is attached to `db_session`. This will cause an error or nothing will happen in the `db` session.

    # To fix this, we should make `override_get_db` return the SAME session as `db_session` if possible,
    # or rely on `db_session` being the one used.

    # Let's adjust the override to use the fixture's session?
    # Cannot easily pass fixture to override.

    # Alternative:
    # Use the `client` with `app.dependency_overrides` where we fix the DB session.
    pass

def test_profile_update_flow(db_session):
    # Better approach: Define overrides inside the test where we have access to db_session

    def override_get_db_session():
        yield db_session

    def override_get_user():
        # Return user attached to this session
        return db_session.query(User).filter(User.email == "test_profile@example.com").first()

    app.dependency_overrides[get_db] = override_get_db_session
    app.dependency_overrides[get_current_user_secure] = override_get_user

    # Create user
    user = User(
        email="test_profile@example.com",
        name="Profile Tester",
        hashed_password="hashed_password",
        is_profile_completed=True,
        github_id="gh_123",
        linkedin_id="li_123"
    )
    db_session.add(user)
    db_session.commit()

    # 1. GET Request
    response = client.get("/dashboard/profile")
    assert response.status_code == 200
    assert "Profile Tester" in response.text

    # 2. POST Request (Update Address)
    payload = {
        "name": "Updated Name",
        "address_street": "New Street",
        "address_number": "100",
        "address_city": "City",
        "billing_same_as_residential": "true" # Form data sends strings mostly
    }

    response = client.post("/dashboard/profile", data=payload)
    assert response.status_code == 200
    assert "Dados atualizados com sucesso!" in response.text

    # Verify DB
    db_session.expire_all()
    updated_user = db_session.query(User).filter(User.email == "test_profile@example.com").first()
    assert updated_user.name == "Updated Name"
    assert updated_user.address_street == "New Street"
    assert updated_user.billing_address_street == "New Street"

    # 3. POST Request (Different Billing)
    payload2 = {
        "name": "Updated Name 2",
        "address_street": "Res Street",
        "billing_same_as_residential": "false",
        "billing_address_street": "Bill Street"
    }

    response = client.post("/dashboard/profile", data=payload2)
    assert response.status_code == 200

    db_session.expire_all()
    updated_user = db_session.query(User).filter(User.email == "test_profile@example.com").first()
    assert updated_user.address_street == "Res Street"
    assert updated_user.billing_address_street == "Bill Street"

    app.dependency_overrides = {}
