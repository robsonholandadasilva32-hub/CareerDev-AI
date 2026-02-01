from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func
from datetime import datetime

# Ajustado para 'app.db.base' para consistência com MLRiskLog
from app.db.base import Base

class RiskSnapshot(Base):
    __tablename__ = "risk_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # --- Métricas Quantitativas (Essenciais para ML/LSTM) ---
    risk_score = Column(Integer, nullable=False)  # 0-100 (Probabilidade/Impacto)
    risk_level = Column(String(10))               # LOW | MEDIUM | HIGH

    # --- Contexto Qualitativo (Audit Trail) ---
    # Tornado nullable=True para permitir snapshots puramente numéricos se necessário
    risk_factor = Column(String, nullable=True)        # Ex: "Obsolescência da Stack" ou "Global"
    mitigation_strategy = Column(String, nullable=True) # Ex: "Aprender Rust"

    # --- Timestamps ---
    recorded_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # --- ESTRATÉGIA INTELIGENTE (Backref) ---
    # Cria a propriedade 'risk_snapshots' dentro do User automaticamente.
    user = relationship(
        "app.db.models.user.User",
        backref=backref("risk_snapshots", cascade="all, delete-orphan")
    )
