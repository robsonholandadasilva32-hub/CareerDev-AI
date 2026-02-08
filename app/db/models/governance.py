from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime
from app.db.base_class import Base

class GovernanceLog(Base):
    __tablename__ = "governance_logs"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String, nullable=False)  # e.g. "SYSTEM_HEARTBEAT", "MODEL_DRIFT_CHECK"
    severity = Column(String, default="INFO")    # e.g. "INFO", "WARNING", "CRITICAL"
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
