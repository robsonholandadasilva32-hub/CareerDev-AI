import datetime
import asyncio
from sqlalchemy.orm import Session
from app.db.models.user import User
from app.db.models.career import CareerProfile
from app.services.social_harvester import social_harvester
from app.db.session import SessionLocal
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

        # 3. Check Hardcore Mode (Gamification Rule)
        # Rule: If streak >= 4 weeks, UNLOCK "HARDCORE MODE"
        is_hardcore = (user.streak_count or 0) >= 4
        if is_hardcore:
             focus_skill = "System Design"
             reasoning = "🔥 HARDCORE MODE ACTIVE: Streak >= 4. Tutorials disabled. Ruthless Challenges only."
             plan_type = "Challenge"

        # 4. Generate Routine
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
        elif plan_type == "Challenge":
            # Hardcore Tasks
            routine = [
                {
                    "id": 1,
                    "day": "Mon",
                    "type": "Design",
                    "task": "System Design: Distributed Rate Limiter",
                    "status": "pending"
                },
                {
                    "id": 2,
                    "day": "Wed",
                    "type": "Code",
                    "task": "Implement Token Bucket Algo in Rust",
                    "verify_key": "rust",
                    "status": "pending"
                },
                 {
                    "id": 3,
                    "day": "Fri",
                    "type": "Code",
                    "task": "Load Test your Rate Limiter",
                    "verify_key": "rust",
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

    def _verify_task_sync(self, user_id: int, task_id: int) -> dict:
        """
        Synchronous logic for task verification.
        Refreshes user data, checks completion, and updates DB.
        """
        with SessionLocal() as db:
            user = db.query(User).get(user_id)
            if not user or not user.career_profile:
                return {"success": False, "message": "User not found or no profile."}

            profile = user.career_profile
            plan = profile.active_weekly_plan

            if not plan:
                return {"success": False, "message": "No active plan."}

            routine = plan.get("routine", [])
            task = next((t for t in routine if t["id"] == task_id), None)

            if not task:
                return {"success": False, "message": "Task not found."}

            if task["status"] == "completed":
                return {"success": True, "message": "Already completed."}

            # Logic: Check metrics (which were just updated by sync_profile)
            metrics = profile.github_activity_metrics or {}
            raw_langs = metrics.get("raw_languages", {})

            verify_key = task.get("verify_key")
            verified = False

            if verify_key:
                 if raw_langs.get(verify_key, raw_langs.get(verify_key.title(), 0)) > 0:
                      verified = True
            else:
                 verified = True

            if verified:
                 task["status"] = "completed"

                 now = datetime.datetime.utcnow()

                 last_check_str = plan.get("last_verified_at")
                 last_check = None
                 if last_check_str:
                     try:
                         last_check = datetime.datetime.fromisoformat(last_check_str)
                     except:
                         pass

                 is_new_week = True
                 if last_check:
                      if last_check.isocalendar()[1] == now.isocalendar()[1] and last_check.year == now.year:
                           is_new_week = False

                 if is_new_week:
                  user.streak_count = (user.streak_count or 0) + 1
                  # user.last_weekly_check does not exist in User model.
                  # We should store it in the plan or profile logic,
                  # but for now we just update streak and rely on plan logic if needed.
                  # Ideally we store last_verified in plan.
                  plan["last_verified_at"] = now.isoformat()

                 profile.active_weekly_plan = dict(plan)
                 db.commit()

                 return {"success": True, "message": "Task Verified! Streak Updated.", "task": task}
            else:
                 return {"success": False, "message": f"No code detected for {verify_key}. Push code to GitHub and try again."}

    async def verify_task(self, db: Session, user: User, task_id: int) -> dict:
        """
        Triggers a SocialHarvester scan and checks if the task can be marked complete.
        """
        if not user.career_profile or not user.career_profile.active_weekly_plan:
            return {"success": False, "message": "No active plan."}

        # Trigger Harvest
        if user.github_token:
             # Use the async harvester
             await social_harvester.sync_profile(user.id, user.github_token)
        else:
             # Simulation / Fail
             return {"success": False, "message": "GitHub Token required for verification."}

        # Reload Profile after sync and verify (Threaded)
        return await asyncio.to_thread(self._verify_task_sync, user.id, task_id)

growth_engine = GrowthEngine()
