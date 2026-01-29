from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func
from app.db.base_class import Base

class RiskSnapshot(Base):
    __tablename__ = "risk_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    risk_factor = Column(String, nullable=False) # Ex: "Obsolescência da Stack"
    risk_score = Column(Integer, nullable=False) # 0-100 (Probabilidade/Impacto)
    mitigation_strategy = Column(String, nullable=True) # Ex: "Aprender Rust"

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # --- ESTRATÉGIA INTELIGENTE (Backref) ---
    # Usamos backref para criar a propriedade 'risk_snapshots' dentro do User automaticamente.
    # Isso evita que tenhamos que abrir o arquivo user.py novamente.
    user = relationship(
        "app.db.models.user.User",
        backref=backref("risk_snapshots", cascade="all, delete-orphan")
    )
