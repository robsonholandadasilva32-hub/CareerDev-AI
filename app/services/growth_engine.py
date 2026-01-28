import logging
from datetime import datetime
from typing import Dict, List, Any
from sqlalchemy.orm import Session
from app.db.models.user import User
from app.db.models.career import CareerProfile
from app.services.social_harvester import social_harvester

logger = logging.getLogger(__name__)

class GrowthEngine:
    """
    The Weekly Growth Engine.
    Analyzes gaps between User Proficiency (GitHub) and Market Trends (LinkedIn/System).
    Generates a targeted weekly plan.
    """

    def generate_weekly_plan(self, db: Session, user: User) -> Dict[str, Any]:
        """
        Generates or returns the existing active plan for the current week.
        """
        profile = user.career_profile
        if not profile:
            # Should not happen in normal flow, but safety check
            return {}

        current_week_id = datetime.utcnow().strftime("%Y-W%U")

        # Check if valid plan exists for this week
        if profile.active_weekly_plan:
            existing_plan = profile.active_weekly_plan
            if existing_plan.get("week_id") == current_week_id:
                return existing_plan

        # Generate New Plan
        new_plan = self._create_plan_logic(profile, current_week_id)

        # Save to DB
        profile.active_weekly_plan = new_plan
        db.commit()

        return new_plan

    def _create_plan_logic(self, profile: CareerProfile, week_id: str) -> Dict[str, Any]:
        """
        Core Algorithm: Gap Analysis & Routine Builder.
        """
        metrics = profile.github_activity_metrics or {}
        raw_langs = metrics.get("raw_languages", {})
        commits = metrics.get("commits_last_30_days", 0)

        # 1. Gap Analysis
        # Identify User's Top Skills
        user_skills = set([k.lower() for k in raw_langs.keys()])

        # Identify Market Demand
        market_demand = social_harvester.market_high_demand_skills

        focus_skill = "System Design" # Default fallback
        reasoning = "Focus on architectural patterns to level up."

        # Find the Gap (Market Skill NOT in User Skills)
        for skill in market_demand:
            if skill.lower() not in user_skills:
                focus_skill = skill
                reasoning = f"Market demands {skill}, but we found no significant code in your GitHub."
                break

        # If no gap (User is a god), Pick a random one to "Master" or "Rust" if missing
        if focus_skill == "System Design" and "rust" not in user_skills:
            focus_skill = "Rust"
            reasoning = "High proficiency detected. Challenge: Master Rust for systems programming."

        # 2. Determine Plan Intensity based on Commit Frequency
        plan_type = "Deep Work"
        if commits < 10:
            plan_type = "Micro-Learning"
            reasoning += " (Low commit volume detected: Starting with 15-min tasks)."

        # 3. Build Routine
        routine = []

        if plan_type == "Micro-Learning":
            routine = [
                {
                    "id": 1,
                    "day": "Mon",
                    "type": "Learn",
                    "task": f"Read: {focus_skill} for Beginners (15 min)",
                    "status": "pending",
                    "verify_type": "manual"
                },
                {
                    "id": 2,
                    "day": "Wed",
                    "type": "Code",
                    "task": f"Hello World: Create a simple {focus_skill} script",
                    "status": "pending",
                    "verify_type": "auto",
                    "verify_url": f"/api/growth/verify",
                    "target_skill": focus_skill
                },
                {
                    "id": 3,
                    "day": "Fri",
                    "type": "Quiz",
                    "task": f"explain-{focus_skill.lower()}-basics",
                    "status": "pending",
                    "verify_type": "manual"
                }
            ]
        else: # Deep Work
            routine = [
                {
                    "id": 1,
                    "day": "Mon",
                    "type": "Architect",
                    "task": f"Design a CLI tool in {focus_skill}",
                    "status": "pending",
                    "verify_type": "manual"
                },
                {
                    "id": 2,
                    "day": "Wed",
                    "type": "Code",
                    "task": f"Push 3 commits to a new {focus_skill} repo",
                    "status": "pending",
                    "verify_type": "auto",
                    "verify_url": f"/api/growth/verify",
                    "target_skill": focus_skill
                },
                 {
                    "id": 3,
                    "day": "Fri",
                    "type": "Refactor",
                    "task": "Optimize memory usage",
                    "status": "pending",
                    "verify_type": "manual"
                }
            ]

        return {
            "week_id": week_id,
            "focus_language": focus_skill,
            "reasoning": reasoning,
            "routine": routine
        }

growth_engine = GrowthEngine()
