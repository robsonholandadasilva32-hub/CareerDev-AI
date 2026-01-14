from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    phone_number = Column(String, nullable=True) # E.164 format ideally

    email_verified = Column(Boolean, default=False, nullable=False)

    preferred_language = Column(String, default="pt")

    two_factor_enabled = Column(Boolean, default=False, nullable=False)
    two_factor_method = Column(String, nullable=True) # 'email' or 'sms'

    # Security Lockout
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    # Subscription
    subscription_status = Column(String, default="free") # 'free', 'active', 'expired'
    subscription_end_date = Column(DateTime, nullable=True)
    is_recurring = Column(Boolean, default=False)
    stripe_customer_id = Column(String, nullable=True)

    # Social Auth
    github_id = Column(String, nullable=True, unique=True)
    linkedin_id = Column(String, nullable=True, unique=True)
    avatar_url = Column(String, nullable=True)

    # Relationships
    career_profile = relationship("CareerProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    learning_plans = relationship("LearningPlan", back_populates="user", cascade="all, delete-orphan")
