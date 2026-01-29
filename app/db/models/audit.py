from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
# Importamos 'backref' aqui
from sqlalchemy.orm import relationship, backref
from datetime import datetime
from app.db.base_class import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True) # Sem index=True para evitar erro
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

    # --- CORREÇÃO FINAL ---
    # Usamos backref=backref(...) para injetar 'audit_logs' no User automaticamente.
    # Isso garante que User e AuditLog estejam sempre sincronizados.
    user = relationship(
        "app.db.models.user.User",
        backref=backref("audit_logs", cascade="all, delete-orphan")
    )
