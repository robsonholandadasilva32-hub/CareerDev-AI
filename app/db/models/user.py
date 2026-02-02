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
    is_admin = Column(Boolean, default=False)
    is_banned = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # --- New/Missing Columns ---
    email_verified = Column(Boolean, default=False)
    is_profile_completed = Column(Boolean, default=False)
    terms_accepted = Column(Boolean, default=False)
    terms_accepted_at = Column(DateTime, nullable=True)
    last_login = Column(DateTime, nullable=True)
    avatar_url = Column(String, nullable=True)

    # --- Integrações Sociais ---
    github_id = Column(String, nullable=True, unique=True)
    github_username = Column(String, nullable=True)
    github_token = Column(String, nullable=True)
    linkedin_profile_url = Column(String, nullable=True)
    linkedin_id = Column(String, nullable=True, unique=True)
    linkedin_token = Column(String, nullable=True)

    # --- Gamification & Dashboard ---
    streak_count = Column(Integer, default=0)
    accelerator_mode = Column(Boolean, default=False)
    last_weekly_check = Column(DateTime, nullable=True)
    
    # --- Relacionamentos ---
    career_profile = relationship("CareerProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    weekly_routines = relationship("WeeklyRoutine", back_populates="user", cascade="all, delete-orphan")
    badges = relationship("UserBadge", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    learning_plans = relationship("LearningPlan", back_populates="user", cascade="all, delete-orphan")

    # --- CAMINHOS COMPLETOS (Blindagem contra erros) ---
    
    # 1. Skill Snapshots
    skill_snapshots = relationship("app.db.models.skill_snapshot.SkillSnapshot", back_populates="user", cascade="all, delete-orphan")

    # 2. Mentor Memories
    mentor_memories = relationship("app.db.models.mentor.MentorMemory", back_populates="user", cascade="all, delete-orphan")

    # 3. Audit Logs (ESSENCIAL: Esta linha deve existir para o erro sumir)
    audit_logs = relationship("app.db.models.audit.AuditLog", back_populates="user", cascade="all, delete-orphan")

    @property
    def name(self):
        return self.full_name

    @name.setter
    def name(self, value):
        self.full_name = value
