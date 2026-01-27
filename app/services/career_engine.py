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
        INJECTED LOGIC: Returns specific data for Robson Holanda (Python/FastAPI -> Rust/Edge AI).
        """
        # Ensure profile analysis runs first to populate data
        self.analyze_profile(db, user)

        # 1. Market Trends (Real-Time Trend Simulation)
        # "High Demand: Edge AI / Low Demand: Basic CRUD"
        market_trends_data = {
            "Edge AI": "High Demand",
            "Basic CRUD": "Low Demand",
            "Rust": "+15%",
            "WASM": "+20%"
        }

        # 2. Skill Gaps (Gap Analysis)
        # Target_Job_Reqs - User_Skills = The_Gap
        # Implied: Rust, AI, GraphDB
        gaps = ["Rust (Memory Safety)", "GraphDB (Neo4j)", "Edge Computing"]

        # 3. Weekly Plan (Micro-Projects & Upskilling Sprint)
        # Card 1: "Refactor Auth Middleware (Security)"
        # Card 2: "Learn Rust Memory Safety"
        weekly_plan_data = [
            {"day": "Mon", "task": "Refactor Auth Middleware (Security)", "status": "pending"},
            {"day": "Tue", "task": "Learn Rust Memory Safety", "status": "pending"},
            {"day": "Wed", "task": "Implement Neo4j Recommendation Engine", "status": "pending"},
            {"day": "Thu", "task": "Study WASM for 3D Avatars", "status": "pending"},
            {"day": "Fri", "task": "Draft LinkedIn Post (Networking)", "status": "pending"}
        ]

        # 4. Skills Radar Data (Scarcity & Upskilling)
        # Visual comparison of Robson's current Python skills vs. Market demand for Rust/AI.
        radar_data = {
            "labels": ['Rust', 'Python', 'AI/ML', 'System Design', 'WebAssembly', 'GraphDB'],
            "datasets": [{
                "label": 'Robson (Current)',
                "data": [30, 95, 40, 60, 20, 10], # High Python, Low Rust/AI
                "backgroundColor": 'rgba(0, 243, 255, 0.2)',
                "borderColor": '#00f3ff',
                "pointBackgroundColor": '#00f3ff',
            }, {
                "label": 'Market Demand (High Value)',
                "data": [95, 60, 90, 85, 90, 80], # High Rust/AI, Lower "Basic" Python importance relative to niche
                "backgroundColor": 'rgba(255, 255, 255, 0.05)',
                "borderColor": '#6b7280',
                "borderDash": [5, 5],
                "pointBackgroundColor": 'transparent'
            }]
        }

        return {
            "market_trends": market_trends_data,
            "skill_gap": gaps,
            "weekly_plan": weekly_plan_data,
            "radar_data": radar_data
        }

career_engine = CareerEngine()
