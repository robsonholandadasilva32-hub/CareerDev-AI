from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from datetime import datetime
from app.db.base import Base

class MentorMemory(Base):
    __tablename__ = "mentor_memories"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    category = Column(String(50))
    content = Column(Text, nullable=False)

    embedding = Column(Text)  # JSON vector
    created_at = Column(DateTime, default=datetime.utcnow)
