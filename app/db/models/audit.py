from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base_class import Base

# --- ATENÇÃO: O nome da classe deve ser LoginHistory ---
class LoginHistory(Base):
    __tablename__ = "login_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    session_id = Column(String, nullable=True)

    # Forensic Data
    ip_address = Column(String, nullable=True)
    user_agent_raw = Column(String, nullable=True)
    device_type = Column(String, nullable=True)
    browser = Column(String, nullable=True)
    os = Column(String, nullable=True)

    # Session Metadata
    login_timestamp = Column(DateTime, default=datetime.utcnow)
    is_active_session = Column(Boolean, default=True)
    auth_method = Column(String, nullable=True)

    # Relacionamento
    user = relationship("User", back_populates="audit_logs")
