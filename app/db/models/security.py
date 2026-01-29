from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base_class import Base
import uuid

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True) # Nullable for login failures where user is unknown? Or just track known users? Let's keep nullable for now if we track system events or failures by IP.
    action = Column(String, nullable=False) # LOGIN, LOGOUT, UPDATE_PROFILE, etc.
    ip_address = Column(String, nullable=True)
    details = Column(Text, nullable=True) # JSON or string details
    created_at = Column(DateTime, default=datetime.utcnow)

    # user = relationship("User", back_populates="audit_logs")


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True) # Optional, can rely on JWT exp, but good for cleanup
    last_active_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    user = relationship("User", back_populates="sessions")
