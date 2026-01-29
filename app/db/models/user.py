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
    
    # 1. Perfil de Carreira
    career_profile = relationship("CareerProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")

    # 2. Rotinas
    weekly_routines = relationship("WeeklyRoutine", back_populates="user", cascade="all, delete-orphan")

    # 3. Badges
    badges = relationship("UserBadge", back_populates="user", cascade="all, delete-orphan")

    # 4. Sessões
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")

    # 5. Planos de Aprendizado
    learning_plans = relationship("LearningPlan", back_populates="user", cascade="all, delete-orphan")

    # 6. Skill Snapshots
    # Usamos o caminho completo para evitar erro de "Multiple classes found" e removemos a duplicata que existia no GitHub
    skill_snapshots = relationship("app.db.models.skill_snapshot.SkillSnapshot", back_populates="user", cascade="all, delete-orphan")

    # 7. Memórias do Mentor (Feature Nova)
    mentor_memories = relationship("MentorMemory", back_populates="user")

    # --- NOTA IMPORTANTE ---
    # O relacionamento 'audit_logs' foi REMOVIDO deste arquivo propositalmente.
    # Ele agora é gerenciado automaticamente pelo 'backref' configurado no arquivo app/db/models/audit.py
    # Isso resolve o conflito de importação circular e ArgumentError.
