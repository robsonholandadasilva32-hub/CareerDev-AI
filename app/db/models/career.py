from sqlalchemy import Column, Integer, String, ForeignKey, JSON, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base_class import Base

class CareerProfile(Base):
    __tablename__ = "career_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    # --- Professional Identity ---
    bio = Column(Text, nullable=True)
    location = Column(String, nullable=True)
    
    # Organization Context (Fixed duplicates)
    company = Column(String(100), nullable=True)
    organization = Column(String(100), nullable=True) # e.g. "Engineering", "Sales"
    team = Column(String(100), nullable=True)         # e.g. "Backend-Core", "Frontend-Infra"
    
    region = Column(String(50), nullable=True)  # ex: LATAM, EU, US
    target_role = Column(String, default="Senior Developer") # e.g., "Rust Engineer"
    
    # --- Seniority & Stack ---
    # Existing field (Legacy compatibility)
    experience_level = Column(String, default="Mid-Level")    
    
    # New Specific Fields
    seniority = Column(String(20))      # Junior | Mid | Senior | Staff
    primary_stack = Column(String(50))  # Python, JS, Rust, etc.

    # --- Skills Analysis (JSON: {"Rust": 80, "Python": 90}) ---
    skills_snapshot = Column(JSON, default={})

    # --- External Data ---
    github_stats = Column(JSON, default={}) # Raw data dump
    linkedin_stats = Column(JSON, default={}) # Raw data dump

    # --- THE HUD DATA STORE ---
    # Stores: { "labels": ["Python", "Rust"], "datasets": [{ "data": [80, 20] }] }
    skills_graph_data = Column(JSON, default={})

    # Stores: { "commits_last_30_days": 120, "top_repo": "career-ai", "velocity_score": "High" }
    github_activity_metrics = Column(JSON, default={})

    # Stores: { "role": "Backend Dev", "industry": "Fintech", "missing_keywords": ["AsyncIO"] }
    linkedin_alignment_data = Column(JSON, default={})

    # --- New AI Analysis Storage (Zone C) ---
    ai_insights_summary = Column(Text, default="")

    # Active Challenge State (Stores {skill: "Docker", question: "...", timestamp: ...})
    active_challenge = Column(JSON, nullable=True)

    # Weekly Growth Plan (JSON: {week_id, focus, routine: []}) - CURRENT ACTIVE PLAN
    active_weekly_plan = Column(JSON, nullable=True)

    # 0-100 Score calculated by intersecting Skills vs. Market Trends
    market_relevance_score = Column(Integer, default=0)

    # Legacy / Helper
    pending_micro_projects = Column(JSON, default=[])    # Kanban/ToDo Widget

    updated_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="career_profile")


class LearningPlan(Base):
    """
    Stores historical weekly plans to generate the 'Streak Bar'.
    Each row represents one finalized week.
    """
    __tablename__ = "learning_plans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Metadata
    week_id = Column(String, nullable=False) # e.g. "2023-W42"
    title = Column(String, nullable=False)   # e.g. "Week 1: Rust Basics"
    description = Column(Text, nullable=True)
    
    # Focus & Strategy
    focus = Column(String, nullable=True)    # e.g. "Rust"
    mode = Column(String, default="GROWTH")  # "GROWTH" or "ACCELERATOR"
    
    # Metrics for Streak Bar
    completion_rate = Column(Integer, default=0) # 0-100% based on tasks completed
    status = Column(String, default="pending")   # pending, in_progress, completed

    # Resources (JSON list of URLs/Tutorials)
    resources = Column(JSON, default=[])

    created_at = Column(DateTime, default=datetime.utcnow)
    due_date = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="learning_plans")
