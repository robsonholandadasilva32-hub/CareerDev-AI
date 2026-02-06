from sqlalchemy.orm import Session
from app.db.models.security import AuditLog, UserSession
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

def create_user_session(db: Session, user_id: int, ip_address: str, user_agent: str) -> str:
    """Creates a persistent session and returns the session ID."""
    try:
        session = UserSession(
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            last_active_at=datetime.utcnow(),
            is_active=True
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        logger.info(f"✅ SESSION CREATED: ID={session.id} User={user_id} IP={ip_address}")
        return session.id
    except Exception as e:
        logger.error(f"❌ SESSION CREATION FAILED: {e}")
        db.rollback()
        raise e

def revoke_session(db: Session, session_id: str):
    """Revokes a session by ID."""
    session = db.query(UserSession).filter(UserSession.id == session_id).first()
    if session:
        session.is_active = False

    # Also revoke from AuditLog (Source of Truth for UI)
    audit = db.query(AuditLog).filter(AuditLog.session_id == session_id).first()
    if audit:
        audit.is_active_session = False

    db.commit()

def log_audit(
    db: Session,
    user_id: int | None,
    action: str,
    ip_address: str,
    details: str | dict = None,
    device_type: str = None,
    browser: str = None,
    os: str = None,
    user_agent_raw: str = None
):
    """Logs a critical action."""
    try:
        if isinstance(details, dict):
            details = json.dumps(details, default=str)

        audit = AuditLog(
            user_id=user_id,
            action=action,
            ip_address=ip_address,
            details=details,
            device_type=device_type,
            browser=browser,
            os=os,
            user_agent_raw=user_agent_raw
        )
        db.add(audit)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to write audit log: {e}")

def get_active_sessions(db: Session, user_id: int):
    """Returns active sessions for a user."""
    return db.query(UserSession).filter(
        UserSession.user_id == user_id,
        UserSession.is_active == True
    ).order_by(UserSession.last_active_at.desc()).all()

def get_all_user_sessions(db: Session, user_id: int):
    """Returns all sessions for a user, ordered by creation date descending."""
    return db.query(UserSession).filter(
        UserSession.user_id == user_id
    ).order_by(UserSession.created_at.desc()).all()

def update_session_activity(db: Session, session_id: str):
    """Updates last_active_at for a session."""
    try:
        session = db.query(UserSession).filter(UserSession.id == session_id).first()
        if session:
            session.last_active_at = datetime.utcnow()
            db.commit()
    except Exception:
        pass # Don't crash on session update failure
