from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base_class import Base

class MentorMemory(Base):
    __tablename__ = "mentor_memories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Campos da memória
    context_key = Column(String, index=True) # Ex: "preferencia_ensino"
    memory_value = Column(Text)              # Ex: "Visual, gosta de diagramas"
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relacionamento Reverso (Caminho completo para segurança)
    user = relationship("app.db.models.user.User", back_populates="mentor_memories")
