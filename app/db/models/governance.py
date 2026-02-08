from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from datetime import datetime
from app.db.base_class import Base

class GovernanceLog(Base):
    __tablename__ = "governance_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    event_type = Column(String(50), nullable=False)
    details = Column(Text, nullable=True)
    severity = Column(String(20), default="INFO")
    created_at = Column(DateTime, default=datetime.utcnow)
