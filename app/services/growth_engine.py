import datetime
from sqlalchemy.orm import Session
from app.db.models.user import User
from app.db.models.career import CareerProfile
from app.services.social_harvester import social_harvester
import logging

logger = logging.getLogger(__name__)

class GrowthEngine:
    """
    The Core Logic for the Weekly Career Accelerator.
    Responsibility:
    1. Gap Analysis (Reality vs Market).
    2. Weekly Plan Generation (Routine).
    3. Task Verification (Proof of Work).
    """

    def __init__(self):
        # Mock Market Trends (In real app, fetch from LinkedIn Jobs API)
        self.market_trends = {
            "Rust": "Very High",
            "Go": "High",
            "Kubernetes": "High",
            "System Design": "Critical",
            "Python": "Stable"
        }

    def generate_weekly_plan(self, db: Session, user: User) -> dict:
        """
        Runs the Gap Analysis Algorithm and generates a personalized weekly routine.
        """
        if not user.career_profile:
            return {}

        profile = user.career_profile
        metrics = profile.github_activity_metrics or {}
        raw_langs = metrics.get("raw_languages", {})

        # 1. Determine Focus
        focus_skill = "Python" # Default
        reasoning = "Standard proficiency check."

        # Logic: Find highest volume skill vs Market
        # Sort user skills by volume
        sorted_user_skills = sorted(raw_langs.items(), key=lambda x: x[1], reverse=True)
        top_skill = sorted_user_skills[0][0] if sorted_user_skills else "General"

        # Scenario: If User = "Python Expert" AND Market = "High Demand for Rust"
        if "Python" in raw_langs and "Rust" not in raw_langs:
             focus_skill = "Rust"
             reasoning = "Detected high Python proficiency but zero systems programming experience (Rust is High Demand)."
        elif "Go" not in raw_langs and "Kubernetes" not in raw_langs:
             focus_skill = "Go"
             reasoning = "Market demands Cloud Native skills. Go is the best entry point."
        else:
             focus_skill = "System Design"
             reasoning = "You have strong coding skills. Time to level up to Architecture."

        # 2. Check Velocity (Constraint)
        velocity = metrics.get("velocity_score", "Low")
        plan_type = "Deep Dive"
        if velocity == "Low":
            plan_type = "Micro-Learning"
            reasoning += " (Adjusted for low availability: 15 min tasks)."

        # 3. Generate Routine
        week_id = datetime.datetime.now().strftime("%Y-W%U")

        routine = [
            {
                "id": 1,
                "day": "Mon",
                "type": "Learn",
                "task": f"Read: {focus_skill} Core Concepts",
                "status": "pending"
            },
            {
                "id": 2,
                "day": "Wed",
                "type": "Code",
                "task": f"CLI Tool: Parse JSON in {focus_skill}",
                "verify_key": focus_skill.lower(), # Key to check in GitHub
                "status": "pending"
            },
            {
                "id": 3,
                "day": "Fri",
                "type": "Code",
                "task": f"Refactor: Optimize {focus_skill} Code",
                "verify_key": focus_skill.lower(),
                "status": "pending"
            }
        ]

        if plan_type == "Micro-Learning":
            # Simplify tasks
            routine = [
                 {
                    "id": 1,
                    "day": "Mon",
                    "type": "Learn",
                    "task": f"15 min: {focus_skill} Syntax",
                    "status": "pending"
                },
                {
                    "id": 2,
                    "day": "Thu",
                    "type": "Code",
                    "task": f"Snippet: Hello World in {focus_skill}",
                    "verify_key": focus_skill.lower(),
                    "status": "pending"
                }
            ]

        plan = {
            "week_id": week_id,
            "focus_language": focus_skill,
            "reasoning": reasoning,
            "routine": routine
        }

        # Save to DB
        profile.active_weekly_plan = plan
        db.commit()

        return plan

    async def verify_task(self, db: Session, user: User, task_id: int) -> dict:
        """
        Triggers a SocialHarvester scan and checks if the task can be marked complete.
        """
        if not user.career_profile or not user.career_profile.active_weekly_plan:
            return {"success": False, "message": "No active plan."}

        plan = user.career_profile.active_weekly_plan
        routine = plan.get("routine", [])

        # Find Task
        task = next((t for t in routine if t["id"] == task_id), None)
        if not task:
            return {"success": False, "message": "Task not found."}

        if task["status"] == "completed":
             return {"success": True, "message": "Already completed."}

        # Trigger Harvest
        if user.github_token:
             # Use the async harvester
             await social_harvester.sync_profile(db, user, user.github_token)
        else:
             # Simulation / Fail
             return {"success": False, "message": "GitHub Token required for verification."}

        # Reload Profile after sync
        db.refresh(user)
        profile = user.career_profile
        metrics = profile.github_activity_metrics or {}
        raw_langs = metrics.get("raw_languages", {})

        # Verification Logic
        # Check if the 'verify_key' (language) exists in raw_languages
        verify_key = task.get("verify_key")

        verified = False
        if verify_key:
             # Check if lang exists
             # In a real scenario, we'd check for *recent* commits in that lang
             # For now, we check if volume > 0 or if velocity is High
             if raw_langs.get(verify_key, raw_langs.get(verify_key.title(), 0)) > 0:
                  verified = True
        else:
             # If no verify key (Learn task), we might just trust them or check login streak
             verified = True # 'Learn' tasks usually manual check, but here we assume button click verifies

        if verified:
             task["status"] = "completed"

             # Check for Streak Update
             # If all tasks completed? Or just one?
             # Let's say if it's the first task completed this week, bump streak?
             # Or just bump streak if they engage.

             # Simple Logic: If not checked in this week, bump streak
             now = datetime.datetime.utcnow()
             last_check = user.last_weekly_check

             is_new_week = True
             if last_check:
                  # Check if same ISO week
                  if last_check.isocalendar()[1] == now.isocalendar()[1] and last_check.year == now.year:
                       is_new_week = False

             if is_new_week:
                  user.weekly_streak_count += 1
                  user.last_weekly_check = now

             # Update Plan in DB (Since we modified the dict in place, we need to reassign to trigger SQLAlchemy update)
             profile.active_weekly_plan = dict(plan)
             db.commit()

             return {"success": True, "message": "Task Verified! Streak Updated.", "task": task}
        else:
             return {"success": False, "message": f"No code detected for {verify_key}. Push code to GitHub and try again."}

growth_engine = GrowthEngine()
