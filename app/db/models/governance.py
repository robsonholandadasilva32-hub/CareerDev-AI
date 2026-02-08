from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.db.base import Base

class GovernanceLog(Base):
    __tablename__ = "governance_logs"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String, index=True) # e.g. "RISK_CHECK"
    severity = Column(String, default="INFO") # INFO, WARNING, CRITICAL
    details = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
