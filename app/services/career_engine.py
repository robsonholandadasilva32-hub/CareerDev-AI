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
        Combines Real Harvested Data with Simulation fallback.
        """
        # Ensure profile analysis runs first to populate data
        self.analyze_profile(db, user)
        profile = user.career_profile

        # 1. Market Trends (Real-Time Trend Simulation)
        market_trends_data = {
            "Edge AI": "High Demand",
            "Basic CRUD": "Low Demand",
            "Rust": "+15%",
            "WASM": "+20%"
        }

        # 2. Skill Gaps (Gap Analysis)
        gaps = ["Rust (Memory Safety)", "GraphDB (Neo4j)", "Edge Computing"]

        # 3. Weekly Plan / Micro Projects
        # Prefer DB persisted plan, fallback to simulation
        weekly_plan_data = profile.pending_micro_projects
        if not weekly_plan_data:
            weekly_plan_data = [
                {"id": 1, "day": "Mon", "task": "Refactor Auth Middleware (Security)", "status": "pending"},
                {"id": 2, "day": "Tue", "task": "Learn Rust Memory Safety", "status": "pending"},
                {"id": 3, "day": "Wed", "task": "Implement Neo4j Recommendation Engine", "status": "pending"},
                {"id": 4, "day": "Thu", "task": "Study WASM for 3D Avatars", "status": "pending"},
                {"id": 5, "day": "Fri", "task": "Draft LinkedIn Post (Networking)", "status": "pending"}
            ]

        # 4. Skills Radar Data (User vs Market)
        radar_data = {
            "labels": ['Rust', 'Python', 'AI/ML', 'System Design', 'WebAssembly', 'GraphDB'],
            "datasets": [{
                "label": 'You (Current)',
                "data": [30, 95, 40, 60, 20, 10],
                "backgroundColor": 'rgba(0, 243, 255, 0.2)',
                "borderColor": '#00f3ff',
                "pointBackgroundColor": '#00f3ff',
            }, {
                "label": 'Market Demand',
                "data": [95, 60, 90, 85, 90, 80],
                "backgroundColor": 'rgba(255, 255, 255, 0.05)',
                "borderColor": '#6b7280',
                "borderDash": [5, 5],
                "pointBackgroundColor": 'transparent'
            }]
        }

        # 5. Repo Composition (Doughnut Chart) - Harvested Data
        doughnut_data = profile.skills_graph_data
        if not doughnut_data:
            # Fallback Simulation
            doughnut_data = {
                "labels": ["Python", "JavaScript", "HTML/CSS"],
                "datasets": [{
                    "data": [70, 20, 10],
                    "backgroundColor": ["#00f3ff", "#bd00ff", "#00ff88"]
                }]
            }

        return {
            "market_trends": market_trends_data,
            "skill_gap": gaps,
            "weekly_plan": weekly_plan_data,
            "radar_data": radar_data,
            "doughnut_data": doughnut_data,
            "market_alignment_score": profile.market_alignment_score or 33 # Default 33
        }

career_engine = CareerEngine()
