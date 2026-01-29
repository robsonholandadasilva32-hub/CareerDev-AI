
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base_class import Base
from app.db.session import get_db
from app.routes.admin import get_current_admin
from app.db.models.user import User

# Setup Test DB
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Verify User model has new columns (it should since we patched the file)
if not hasattr(User, 'is_admin'):
    raise RuntimeError("User model missing is_admin in test environment!")

@pytest.fixture(scope="module")
def init_db():
    # Import all models to ensure they are registered
    # We can try to rely on imports in app.main or just import what we need
    # Ideally we should import everything but for this test maybe just User is enough?
    # No, User has relationships.
    # Let's hope create_all works if we import enough.

    # We need to import modules that define models to register them
    try:
        from app.db.models import career, gamification, security, audit, mentor, skill_snapshot
    except ImportError:
        pass

    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session(init_db):
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    # Override admin auth
    def override_get_admin():
        return User(id=1, email="admin@example.com", is_admin=True, full_name="Admin")

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_admin] = override_get_admin

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()

def test_admin_dashboard_pagination(client, db_session):
    # Seed 60 users
    users = []
    for i in range(60):
        users.append(User(
            email=f"user{i}@test.com",
            hashed_password="hash",
            full_name=f"User {i}",
            is_active=True,
            is_admin=False,
            is_banned=False
        ))
    db_session.add_all(users)
    db_session.commit()

    # Request page 1 (limit default 50)
    response = client.get("/admin/dashboard")
    assert response.status_code == 200
    content = response.text
    # Check for pagination text
    assert "Page 1 of 2" in content
    assert "Total: 60" in content
    assert "Next &rarr;" in content
    assert "Previous" not in content # Should not be on page 1

    # Request page 2
    response = client.get("/admin/dashboard?page=2&limit=50")
    assert response.status_code == 200
    content = response.text
    assert "Page 2 of 2" in content
    assert "Previous" in content
    assert "Next &rarr;" not in content # Should not be on last page

    # Check user count in page 2 (should be 10)
    # We can count occurences of "row-" IDs or similar.
    # User 50 to 59
    assert "user50@test.com" in content
    assert "user0@test.com" not in content
