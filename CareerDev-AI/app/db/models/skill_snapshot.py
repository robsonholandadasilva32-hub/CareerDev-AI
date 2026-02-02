from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base_class import Base

class SkillSnapshot(Base):
    __tablename__ = "skill_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    skill = Column(String, nullable=False)
    confidence_score = Column(Integer, nullable=False)  # 0–100

    # Usar server_default=func.now() é mais seguro para bancos de dados
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())

    # --- CAMINHO COMPLETO ---
    # Aponta explicitamente para o User para evitar erros de registro duplicado
    user = relationship("app.db.models.user.User", back_populates="skill_snapshots")
