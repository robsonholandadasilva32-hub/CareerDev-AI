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

    def analyze_profile(self, db: Session, user: User) -> Dict:
        """
        Analyzes the user profile, fetching external data if available,
        and updates/creates the CareerProfile in the DB.
        """
        if not user:
            return {}

        profile = user.career_profile
        if not profile:
            profile = CareerProfile(user_id=user.id)
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

    def generate_plan(self, db: Session, user: User) -> List[LearningPlan]:
        """
        Generates or retrieves the current learning plan.
        """
        # Check existing incomplete items
        existing_plan = db.query(LearningPlan).filter(
            LearningPlan.user_id == user.id,
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
                user_id=user.id,
                title="Fundamentos de Rust",
                description="Domine Ownership e Borrowing com o Rust Book.",
                technology="Rust",
                resources=["https://doc.rust-lang.org/book/"],
                due_date=datetime.utcnow() + timedelta(days=7)
            ))

        if skills.get("Go", 0) < 30:
             new_items.append(LearningPlan(
                user_id=user.id,
                title="Microsserviços com Go",
                description="Crie uma API RESTful usando Gin ou Echo.",
                technology="Go",
                due_date=datetime.utcnow() + timedelta(days=7)
            ))

        # Always add an AI Ethics item
        # Ensure user_id is passed explicitly from user.id
        new_items.append(LearningPlan(
            user_id=user.id,
            title="Introdução à IA Ética",
            description="Entenda os princípios de explicabilidade e viés algorítmico.",
            technology="AI Ethics",
            due_date=datetime.utcnow() + timedelta(days=14)
        ))

        db.add_all(new_items)
        db.commit()

        return new_items

    def get_career_dashboard_data(self, db: Session, user: User) -> Dict:
        """
        Returns the structured JSON object for the new Dashboard AI brain.
        Includes Market Trends, Skill Gaps, and Weekly Micro-Projects.
        """
        # Ensure profile analysis runs first to populate data
        self.analyze_profile(db, user)

        # Market Trends (Mocked for now, but following the spec)
        market_trends_data = {
            "rust": "+15%",
            "go": "+12%",
            "python": "stable",
            "wasm": "+20%"
        }

        # Skill Gaps
        # Logic: If they have low Rust/Go, flag it.
        profile = user.career_profile
        skills = profile.skills_snapshot if profile else {}

        gaps = []
        if skills.get("Rust", 0) < 40:
            gaps.append("Rust (Ownership)")
        if skills.get("Go", 0) < 40:
            gaps.append("Go (Concurrency)")
        if skills.get("System Design", 0) < 50:
            gaps.append("System Design")

        # Default gaps if none found (fallback)
        if not gaps:
            gaps = ["AsyncIO", "Kubernetes", "System Design"]

        # Weekly Plan (Micro-Projects)
        # Map existing LearningPlan items to the requested format
        plans = self.generate_plan(db, user)
        weekly_plan_data = []

        days = ["Mon", "Tue", "Wed", "Thu", "Fri"]
        for i, plan in enumerate(plans[:5]):
            weekly_plan_data.append({
                "day": days[i] if i < len(days) else "Weekend",
                "task": plan.title, # e.g. "Implement a gRPC server"
                "status": "pending" if plan.status != 'completed' else "completed"
            })

        # Fallback if no plans
        if not weekly_plan_data:
             weekly_plan_data = [
                 {"day": "Mon", "task": "Implement a gRPC server", "status": "pending"},
                 {"day": "Tue", "task": "Rust: Ownership Drills", "status": "pending"},
                 {"day": "Wed", "task": "Study Raft Consensus", "status": "pending"}
             ]

        return {
            "market_trends": market_trends_data,
            "skill_gap": gaps,
            "weekly_plan": weekly_plan_data
        }

career_engine = CareerEngine()
