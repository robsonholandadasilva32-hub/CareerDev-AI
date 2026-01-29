from sqlalchemy import Column, Integer, DateTime, String, ForeignKey
from datetime import datetime
from app.db.base import Base

class MLRiskLog(Base):
    __tablename__ = "ml_risk_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    ml_risk = Column(Integer)
    rule_risk = Column(Integer)
    model_version = Column(String(10))
    created_at = Column(DateTime, default=datetime.utcnow)
