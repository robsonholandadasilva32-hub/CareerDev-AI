from sqlalchemy import Column, Integer, String, JSON, DateTime, Text
from sqlalchemy.sql import func
from app.db.base import Base

class BackgroundJob(Base):
    __tablename__ = "background_jobs"

    id = Column(Integer, primary_key=True, index=True)
    task_type = Column(String, index=True) # e.g., 'send_email', 'send_telegram'
    payload = Column(JSON) # Stores args like {'to': '...', 'code': '123'}
    status = Column(String, default="pending") # pending, completed, failed
    attempts = Column(Integer, default=0)
    error_log = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
