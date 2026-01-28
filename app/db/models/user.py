# ... (imports anteriores mantidos) ...
from app.db.base_class import Base

class User(Base):
    __tablename__ = "users"
    
    # ... (mesmos campos de antes) ...
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # ... (outros campos mantidos) ...
    github_username = Column(String, nullable=True)
    github_token = Column(String, nullable=True)
    linkedin_profile_url = Column(String, nullable=True)
    streak_count = Column(Integer, default=0)
    accelerator_mode = Column(Boolean, default=False)
    
    # --- Relacionamentos ---
    career_profile = relationship("CareerProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    weekly_routines = relationship("WeeklyRoutine", back_populates="user", cascade="all, delete-orphan")
    badges = relationship("UserBadge", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    learning_plans = relationship("LearningPlan", back_populates="user", cascade="all, delete-orphan")
    
    # CORREÇÃO AQUI: Mudei de "LoginHistory" para "AuditLog"
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")
