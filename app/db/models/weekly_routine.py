from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

# Importe do arquivo isolado base_class
from app.db.base_class import Base

class WeeklyRoutine(Base):
    __tablename__ = "weekly_routines"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    week_id = Column(String(10), nullable=False)  # ex: 2026-W05
    mode = Column(String(20), default="GROWTH")   # GROWTH | HARDCORE | ACCELERATOR
    focus = Column(String(50), nullable=False)

    tasks = Column(JSON, nullable=False)          # Lista de tarefas
    suggested_pr = Column(JSON, nullable=True)

    completed = Column(Boolean, default=False)
    completion_rate = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="weekly_routines")
