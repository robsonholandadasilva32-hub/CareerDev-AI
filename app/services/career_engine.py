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
        Phase 3 Compliance: Strict JSON structure for HUD.
        """
        # Ensure profile analysis runs first to populate data
        self.analyze_profile(db, user)
        profile = user.career_profile

        # ZONE A: REALITY (Doughnut Chart)
        doughnut_data = profile.skills_graph_data
        insight_text = "Analysis Pending..."

        if doughnut_data and "labels" in doughnut_data:
            labels = doughnut_data["labels"]
            datasets = doughnut_data.get("datasets", [])
            values = datasets[0]["data"] if datasets else []

            # Simple Insight Logic
            if "Python" in labels and "Go" not in labels:
                 insight_text = "You are tech-heavy on Python, but the market is moving to Go."
            elif "Rust" in labels:
                 insight_text = "Strong Market Alignment detected with Rust."
            else:
                 insight_text = "Consider diversifying your stack with Systems Languages."
        else:
             # Fallback Simulation if Harvester hasn't run
             doughnut_data = {
                 "labels": ["Python", "Go"],
                 "datasets": [{"data": [85, 15], "backgroundColor": ["#00f3ff", "#bd00ff"]}]
             }
             insight_text = "You are tech-heavy on Python, but the market is moving to Go."

        # ZONE B: ACTION (Kanban)
        # Convert stored plan to "Zone B" format
        raw_plan = profile.pending_micro_projects
        if not raw_plan:
             # Fallback
             zone_b_action = [
                 { "id": 1, "title": "Build a gRPC Service in Go", "status": "pending", "type": "upskilling" },
                 { "id": 2, "title": "Refactor Auth with Rust", "status": "pending", "type": "upskilling" },
                 { "id": 3, "title": "Deploy to K8s", "status": "pending", "type": "infrastructure" }
             ]
        else:
             # Normalize if older format
             zone_b_action = []
             for item in raw_plan:
                 # Map 'task' to 'title' if needed
                 title = item.get("title") or item.get("task") or "Unknown Task"
                 zone_b_action.append({
                     "id": item.get("id"),
                     "title": title,
                     "status": item.get("status", "pending"),
                     "type": item.get("type", "upskilling")
                 })

        # ZONE C: TICKER (Score)
        score = profile.market_relevance_score or 0
        pulse = "Stable"
        if score > 70: pulse = "High Demand"
        elif score < 40: pulse = "Needs Update"

        return {
            "zone_a_reality": {
                "chart_type": "doughnut",
                "data": {
                    "labels": doughnut_data.get("labels", []),
                    "values": doughnut_data.get("datasets", [{}])[0].get("data", [])
                },
                "insight": insight_text
            },
            "zone_b_action": zone_b_action,
            "zone_c_ticker": {
                "user_score": score,
                "market_pulse": pulse
            }
        }

career_engine = CareerEngine()
