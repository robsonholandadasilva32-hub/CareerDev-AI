from sqlalchemy import Column, Integer, String, ForeignKey, JSON, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base

class CareerProfile(Base):
    __tablename__ = "career_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    # Professional Identity
    bio = Column(Text, nullable=True)
    location = Column(String, nullable=True)
    target_role = Column(String, default="Senior Developer") # e.g., "Rust Engineer"
    experience_level = Column(String, default="Mid-Level")   # Junior, Mid, Senior

    # Skills Analysis (JSON: {"Rust": 80, "Python": 90})
    skills_snapshot = Column(JSON, default={})

    # External Data
    github_stats = Column(JSON, default={}) # {"repos": 10, "top_lang": "Python"}
    linkedin_stats = Column(JSON, default={})

    updated_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="career_profile")


class LearningPlan(Base):
    __tablename__ = "learning_plans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    title = Column(String, nullable=False) # e.g. "Week 1: Rust Basics"
    description = Column(Text, nullable=True)
    technology = Column(String, nullable=True) # "Rust", "Go"

    # Status: pending, in_progress, completed
    status = Column(String, default="pending")

    # Resources (JSON list of URLs/Tutorials)
    resources = Column(JSON, default=[])

    created_at = Column(DateTime, default=datetime.utcnow)
    due_date = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="learning_plans")
