from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime
)
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.declarative import Base


class User(Base):
    __tablename__ = "users"

    # -------------------------------------------------
    # Core Identity
    # -------------------------------------------------
    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    email_verified = Column(Boolean, default=True, nullable=False)
    preferred_language = Column(String, default="pt")

    avatar_url = Column(String, nullable=True)

    # -------------------------------------------------
    # Authentication & Security
    # -------------------------------------------------
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    is_premium = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    is_banned = Column(Boolean, default=False)

    # -------------------------------------------------
    # Social Authentication
    # -------------------------------------------------
    github_id = Column(String, nullable=True, unique=True)
    github_username = Column(String, nullable=True)
    github_token = Column(String, nullable=True)

    linkedin_id = Column(String, nullable=True, unique=True)
    linkedin_token = Column(String, nullable=True)

    # -------------------------------------------------
    # Gamification & Productivity
    # -------------------------------------------------
    weekly_streak_count = Column(Integer, default=0)
    streak_count = Column(Integer, default=0)  # compat / evolution
    last_weekly_check = Column(DateTime, nullable=True)

    accelerator_mode = Column(Boolean, default=False)

    # -------------------------------------------------
    # Residential Address
    # -------------------------------------------------
    address_street = Column(String, nullable=True)
    address_number = Column(String, nullable=True)
    address_complement = Column(String, nullable=True)
    address_city = Column(String, nullable=True)
    address_state = Column(String, nullable=True)
    address_zip_code = Column(String, nullable=True)
    address_country = Column(String, nullable=True)

    # -------------------------------------------------
    # Onboarding & Compliance
    # -------------------------------------------------
    is_profile_completed = Column(Boolean, default=False)
    terms_accepted = Column(Boolean, default=False)
    terms_accepted_at = Column(DateTime, nullable=True)

    # -------------------------------------------------
    # Relationships
    # -------------------------------------------------
    career_profile = relationship(
        "CareerProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )

    learning_plans = relationship(
        "LearningPlan",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    weekly_routines = relationship(
        "WeeklyRoutine",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    badges = relationship(
        "UserBadge",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    # -------------------------------------------------
    # Security Relationships
    # -------------------------------------------------
    audit_logs = relationship(
        "AuditLog",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    sessions = relationship(
        "UserSession",
        back_populates="user",
        cascade="all, delete-orphan"
    )
