import pytest
from fastapi.testclient import TestClient
from app.main import app as fastapi_app
from app.db.session import SessionLocal, engine, get_db
import app.db.session
from sqlalchemy.pool import StaticPool
from sqlalchemy import create_engine
import app.db.base
from app.db.base_class import Base
from app.db.models.user import User
from app.db.models.security import AuditLog
from app.routes.admin import get_current_admin
from datetime import datetime

@pytest.fixture(scope="module")
def setup_engine():
    # Use StaticPool to share sqlite memory across connections
    new_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    app.db.session.engine = new_engine
    app.db.session.SessionLocal.configure(bind=new_engine)
    return new_engine

@pytest.fixture
def db(setup_engine):
    Base.metadata.create_all(bind=setup_engine)
    session = app.db.session.SessionLocal()
    yield session
    session.rollback()
    session.close()
    Base.metadata.drop_all(bind=setup_engine)

@pytest.fixture
def client(db):
    def override_get_db():
        yield db
    print(f"DEBUG: Type of fastapi_app is {type(fastapi_app)}")
    fastapi_app.dependency_overrides[get_db] = override_get_db
    return TestClient(fastapi_app)

def test_admin_dashboard_flagged_users(client, db):
    # 1. Create Admin User
    admin = User(email="admin@example.com", is_admin=True, hashed_password="pw", full_name="Admin")
    db.add(admin)
    db.commit()
    db.refresh(admin)

    # Override dependency to return this admin
    fastapi_app.dependency_overrides[get_current_admin] = lambda: admin

    # 2. Create Banned User
    banned = User(email="banned@example.com", is_banned=True, hashed_password="pw", full_name="Banned")
    db.add(banned)

    # 3. Create Suspicious User (with WARNING log)
    suspicious = User(email="suspicious@example.com", is_banned=False, hashed_password="pw", full_name="Suspicious")
    db.add(suspicious)
    db.commit() # Get IDs

    log = AuditLog(
        user_id=suspicious.id,
        action="WARNING",
        login_timestamp=datetime.utcnow(),
        details="Suspicious login"
    )
    db.add(log)

    # 4. Create Normal User
    normal = User(email="normal@example.com", is_banned=False, hashed_password="pw", full_name="Normal")
    db.add(normal)
    db.commit()

    # 5. Request Dashboard
    response = client.get("/admin/dashboard")
    assert response.status_code == 200
    html = response.text

    # Verify High Priority Section exists
    assert "High Priority Alerts" in html

    # Verify Banned User is listed
    assert "banned@example.com" in html
    assert "Account Banned" in html

    # Verify Suspicious User is listed
    assert "suspicious@example.com" in html
    assert "Suspicious Activity" in html

    # Verify Normal User is listed (somewhere in the page, as part of pagination)
    assert "normal@example.com" in html

    # Clean up overrides
    fastapi_app.dependency_overrides = {}
