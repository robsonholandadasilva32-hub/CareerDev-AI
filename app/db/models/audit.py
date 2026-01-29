from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base_class import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"
    # Mantemos isso para garantir que ele sobrescreva definições antigas na memória
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    session_id = Column(String, nullable=True)

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

    # --- CORREÇÃO DEFINITIVA ---
    # Usando o caminho COMPLETO para evitar erros cíclicos ou de ambiguidade
    user = relationship("app.db.models.user.User", back_populates="audit_logs")
