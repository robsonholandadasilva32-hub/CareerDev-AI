from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base_class import Base

class User(Base):
    __tablename__ = "users"

    # --- Identidade Core ---
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False) # Essencial para o Login
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # --- Integrações Sociais ---
    github_username = Column(String, nullable=True)
    github_token = Column(String, nullable=True) # Token OAuth criptografado
    linkedin_profile_url = Column(String, nullable=True)

    # --- Gamification & Dashboard ---
    streak_count = Column(Integer, default=0) # Usado no Dashboard (Hardcore Mode)
    accelerator_mode = Column(Boolean, default=False) # Ativa features avançadas
    
    # --- Relacionamentos (Cruciais para o dashboard.py funcionar) ---
    
    # 1. Perfil de Carreira (One-to-One)
    # Contém as skills, métricas do GitHub e análise de gaps
    career_profile = relationship("CareerProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")

    # 2. Rotinas Semanais (One-to-Many)
    # O plano gerado pelo CareerEngine
    weekly_routines = relationship("WeeklyRoutine", back_populates="user", cascade="all, delete-orphan")

    # 3. Badges/Conquistas (One-to-Many)
    # Necessário para o joinedload(User.badges) no dashboard
    badges = relationship("UserBadge", back_populates="user", cascade="all, delete-orphan")

    # 4. Sessões de Segurança (One-to-Many)
    # Para o painel de Segurança e controle de dispositivos
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")

    # 5. Planos de Aprendizado (Legacy/Compatibilidade)
    learning_plans = relationship("LearningPlan", back_populates="user", cascade="all, delete-orphan")
