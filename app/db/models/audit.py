from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base_class import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"
    # Mantemos extend_existing para segurança
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True) # Sem index=True
    user_id = Column(Integer, ForeignKey("users.id"))
    session_id = Column(String, nullable=True)
    action = Column(String, nullable=True) # Added to resolve conflict with security.py
    details = Column(String, nullable=True) # Added to resolve conflict with security.py

    # Dados Forenses
    ip_address = Column(String, nullable=True)
    user_agent_raw = Column(String, nullable=True)
    device_type = Column(String, nullable=True)
    browser = Column(String, nullable=True)
    os = Column(String, nullable=True)

    # Metadados
    login_timestamp = Column(DateTime, default=datetime.utcnow)
    is_active_session = Column(Boolean, default=True)
    auth_method = Column(String, nullable=True)

    # --- RELACIONAMENTO ---
    # Aponta para User com caminho completo e espera encontrar 'audit_logs' lá
    # Including both to satisfy user request and fix the warning
    user = relationship("app.db.models.user.User", back_populates="audit_logs", overlaps="audit_logs, user")
