import httpx
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import json

from app.db.models.user import User
from app.db.models.career import CareerProfile, LearningPlan

class CareerEngine:
    def __init__(self):
        # In a real app, these would come from an external API or LLM analysis
        self.market_trends = {
            "Rust": "High",
            "Go": "Very High",
            "Python": "Stable",
            "Ethical AI": "Emerging"
        }

    def analyze_profile(self, db: Session, user_id: int) -> Dict:
        """
        Analyzes the user profile, fetching external data if available,
        and updates/creates the CareerProfile in the DB.
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {}

        profile = user.career_profile
        if not profile:
            profile = CareerProfile(user_id=user_id)
            db.add(profile)
            db.commit()
            db.refresh(profile)

        # 1. Sync External Data (Simulation)
        if user.github_id and not profile.github_stats:
            # Simulate GitHub fetching
            # Real implementation would use: httpx.get(f"https://api.github.com/user/{user.github_id}")
            profile.github_stats = {
                "repos": 12,
                "top_languages": {"Python": 60, "JavaScript": 30, "Rust": 10},
                "last_commit": datetime.utcnow().isoformat()
            }
            # Update skills based on GH
            current_skills = profile.skills_snapshot or {}
            current_skills.update({"Rust": 20, "Python": 80}) # Mocked inference
            profile.skills_snapshot = current_skills
            db.commit()

        # 2. Return Structured Data
        return {
            "skills": profile.skills_snapshot or {"General": 10},
            "level": profile.experience_level,
            "focus": profile.target_role,
            "trends": self.market_trends
        }

    def generate_plan(self, db: Session, user_id: int) -> List[LearningPlan]:
        """
        Generates or retrieves the current learning plan.
        """
        user = db.query(User).filter(User.id == user_id).first()

        # Check existing incomplete items
        existing_plan = db.query(LearningPlan).filter(
            LearningPlan.user_id == user_id,
            LearningPlan.status != "completed"
        ).all()

        if existing_plan:
            return existing_plan

        # Generate new items based on gaps
        new_items = []
        profile = user.career_profile
        skills = profile.skills_snapshot if profile else {}

        # Gaps Analysis (Heuristic)
        if skills.get("Rust", 0) < 30:
            new_items.append(LearningPlan(
                user_id=user_id,
                title="Fundamentos de Rust",
                description="Domine Ownership e Borrowing com o Rust Book.",
                technology="Rust",
                resources=["https://doc.rust-lang.org/book/"],
                due_date=datetime.utcnow() + timedelta(days=7)
            ))

        if skills.get("Go", 0) < 30:
             new_items.append(LearningPlan(
                user_id=user_id,
                title="Microsserviços com Go",
                description="Crie uma API RESTful usando Gin ou Echo.",
                technology="Go",
                due_date=datetime.utcnow() + timedelta(days=7)
            ))

        # Always add an AI Ethics item
        new_items.append(LearningPlan(
            user_id=user_id,
            title="Introdução à IA Ética",
            description="Entenda os princípios de explicabilidade e viés algorítmico.",
            technology="AI Ethics",
            due_date=datetime.utcnow() + timedelta(days=14)
        ))

        db.add_all(new_items)
        db.commit()

        # Refresh to get IDs
        for item in new_items:
            db.refresh(item)

        return new_items

career_engine = CareerEngine()
