from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base_class import Base

class GovernanceLog(Base):
    __tablename__ = "governance_logs"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(50), nullable=False)  # e.g. "RISK_SPIKE", "SYSTEM_CHECK"
    severity = Column(String(20), default="INFO")    # INFO, WARNING, CRITICAL
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Nullable User ID (The Hybrid Approach)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
