import pytest
import uuid
from sqlalchemy.orm import Session
from app.db.session import SessionLocal, engine
import app.db.base  # Register all models
from app.db.base_class import Base
from app.db.models.user import User
from app.db.models.security import UserSession, AuditLog
from app.services.security_service import revoke_session
from datetime import datetime

@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()
    Base.metadata.drop_all(bind=engine)

def test_revoke_session_updates_audit_log(db: Session):
    # 1. Create a dummy user
    user = User(
        email=f"test_revoke_{uuid.uuid4()}@example.com",
        hashed_password="hashed_secret",
        full_name="Test Revoke",
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # 2. Create a session ID
    session_id = str(uuid.uuid4())

    # 3. Create UserSession
    user_session = UserSession(
        id=session_id,
        user_id=user.id,
        is_active=True,
        last_active_at=datetime.utcnow()
    )
    db.add(user_session)

    # 4. Create AuditLog entry linked to this session
    audit_log = AuditLog(
        user_id=user.id,
        action="LOGIN",
        ip_address="127.0.0.1",
        session_id=session_id,
        is_active_session=True,
        login_timestamp=datetime.utcnow()
    )
    db.add(audit_log)
    db.commit()

    # Verify initial state
    assert db.query(UserSession).filter_by(id=session_id).one().is_active is True
    assert db.query(AuditLog).filter_by(session_id=session_id).one().is_active_session is True

    # 5. Call revoke_session
    revoke_session(db, session_id)

    # 6. Verify end state
    # Refresh objects
    db.expire_all()

    updated_session = db.query(UserSession).filter_by(id=session_id).one()
    updated_audit = db.query(AuditLog).filter_by(session_id=session_id).one()

    assert updated_session.is_active is False
    assert updated_audit.is_active_session is False
