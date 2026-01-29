from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base_class import Base

class User(Base):
    __tablename__ = "users"

    # --- Identidade Core ---
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # --- Integrações Sociais ---
    github_username = Column(String, nullable=True)
    github_token = Column(String, nullable=True)
    linkedin_profile_url = Column(String, nullable=True)

    # --- Gamification & Dashboard ---
    streak_count = Column(Integer, default=0)
    accelerator_mode = Column(Boolean, default=False)
    
    # --- Relacionamentos ---
    career_profile = relationship("CareerProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    weekly_routines = relationship("WeeklyRoutine", back_populates="user", cascade="all, delete-orphan")
    badges = relationship("UserBadge", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    learning_plans = relationship("LearningPlan", back_populates="user", cascade="all, delete-orphan")
    skill_snapshots = relationship("app.db.models.skill_snapshot.SkillSnapshot", back_populates="user", cascade="all, delete-orphan")
    
    # --- CORREÇÃO DEFINITIVA ---
    # Usando o caminho COMPLETO para eliminar a ambiguidade "Multiple classes found"
    audit_logs = relationship("app.db.models.audit.AuditLog", back_populates="user", cascade="all, delete-orphan")
