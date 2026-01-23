import pytest
from app.db.session import SessionLocal, engine
from app.db.models.user import User
from app.db.models.security import AuditLog, UserSession
from app.services.security_service import create_user_session, log_audit, revoke_session, get_active_sessions
from app.core.jwt import create_access_token
from fastapi.testclient import TestClient
from app.main import app
from app.db.declarative import Base
import uuid

# Create tables
Base.metadata.create_all(bind=engine)

client = TestClient(app)

@pytest.fixture
def db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_security_service(db):
    # Setup User
    email = f"test_{uuid.uuid4()}@example.com"
    user = User(name="Test Security", email=email, hashed_password="pw", is_profile_completed=True, terms_accepted=True)
    db.add(user)
    db.commit()
    db.refresh(user)

    # 1. Create Session
    sid = create_user_session(db, user.id, "127.0.0.1", "TestAgent")
    assert sid is not None

    session = db.query(UserSession).filter(UserSession.id == sid).first()
    assert session.is_active is True
    assert session.user_id == user.id

    # 2. Log Audit
    log_audit(db, user.id, "TEST_ACTION", "127.0.0.1", "Details")
    log = db.query(AuditLog).filter(AuditLog.user_id == user.id).first()
    assert log is not None
    assert log.action == "TEST_ACTION"

    # 3. Get Active Sessions
    sessions = get_active_sessions(db, user.id)
    # Note: Depending on cleanup, might have others, but we check presence
    sids = [s.id for s in sessions]
    assert sid in sids

    # 4. Revoke
    revoke_session(db, sid)
    session = db.query(UserSession).filter(UserSession.id == sid).first()
    assert session.is_active is False

    sessions = get_active_sessions(db, user.id)
    sids = [s.id for s in sessions]
    assert sid not in sids

def test_middleware_enforcement(db):
    # Setup User
    email = f"mw_{uuid.uuid4()}@example.com"
    user = User(name="MW Test", email=email, hashed_password="pw", is_profile_completed=True, terms_accepted=True)
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create Valid Session
    sid = create_user_session(db, user.id, "127.0.0.1", "TestAgent")

    # Create Token with SID
    token = create_access_token({"sub": str(user.id), "sid": sid})

    # Protected Endpoint
    client.cookies.set("access_token", token)

    # 1. Valid Request
    # /dashboard/security does not trigger external API calls, safe for test
    response = client.get("/dashboard/security")

    # If 302 to /login, then auth failed.
    if response.status_code == 302:
        assert "/login" not in response.headers["location"]
    assert response.status_code == 200

    # 2. Revoke Session
    revoke_session(db, sid)

    # 3. Request with Revoked Session -> Should Redirect to Login
    response = client.get("/dashboard/security", follow_redirects=False)
    assert response.status_code in [302, 307]
    assert "/login" in response.headers["location"]
