from sqlalchemy import Column, Integer, DateTime, String, ForeignKey
from datetime import datetime
from app.db.base import Base

class MLRiskLog(Base):
    __tablename__ = "ml_risk_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    # Pontuações de Risco
    ml_risk = Column(Integer)       # Score gerado pela IA
    rule_risk = Column(Integer)     # Score gerado pelas regras estáticas
    final_risk = Column(Integer)    # Score final consolidado (usado na UI)

    # MLOps & A/B Testing
    model_version = Column(String(20))     # Ex: "v1.0.2-beta"
    experiment_group = Column(String(10))  # Ex: "A" (Control) ou "B" (Test)

    created_at = Column(DateTime, default=datetime.utcnow)
