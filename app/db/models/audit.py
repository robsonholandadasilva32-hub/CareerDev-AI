from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base_class import Base

# CORREÇÃO: O nome da classe DEVE ser LoginHistory (não AuditLog)
class LoginHistory(Base):
    __tablename__ = "login_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    session_id = Column(String, nullable=True) # Link to UserSession.id

    # Forensic Data
    ip_address = Column(String, nullable=True)
    user_agent_raw = Column(String, nullable=True)
    device_type = Column(String, nullable=True) # Desktop / Mobile / Tablet
    browser = Column(String, nullable=True)
    os = Column(String, nullable=True)

    # Session Metadata
    login_timestamp = Column(DateTime, default=datetime.utcnow)
    is_active_session = Column(Boolean, default=True)
    auth_method = Column(String, nullable=True)

    # Relacionamento Reverso
    # Aqui dizemos que este registro pertence a um "User" e se conecta via "audit_logs"
    user = relationship("User", back_populates="audit_logs")

    # TODO: Implement a Cron Job to archive/delete logs older than 1 year.
