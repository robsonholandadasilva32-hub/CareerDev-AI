import datetime
import asyncio
from sqlalchemy.orm import Session
from app.db.models.user import User
from app.db.models.career import CareerProfile
from app.db.models.weekly_routine import WeeklyRoutine
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
        commits_30d = metrics.get("commits_last_30_days", 0)

        # 1. Determine Focus (Gap Analysis)
        total_bytes = sum(raw_langs.values())
        python_bytes = raw_langs.get("Python", 0)
        python_share = (python_bytes / total_bytes) if total_bytes > 0 else 0

        focus_skill = "Python" # Default
        reasoning = "Standard proficiency check."

        # Rule 1: Gap Analysis (Python Dominance -> Force Rust)
        if python_share > 0.8 and "Rust" not in raw_langs:
             focus_skill = "Rust"
             reasoning = "Gap Analysis: High Python dominance (>80%) detected. Market trends indicate Rust as high-value expansion."
        elif "Go" not in raw_langs and "Kubernetes" not in raw_langs:
             focus_skill = "Go"
             reasoning = "Market demands Cloud Native skills. Go is the best entry point."
        else:
             # Sort logic
             sorted_user_skills = sorted(raw_langs.items(), key=lambda x: x[1], reverse=True)
             top_skill = sorted_user_skills[0][0] if sorted_user_skills else "General"
             if top_skill == focus_skill:
                  # If default matches top, suggest Deep Dive or Architecture
                  focus_skill = "System Design" if python_share > 0.5 else top_skill
                  reasoning = "Deepening expertise in primary stack."

        # 2. Check Velocity (Micro-Learning Constraint)
        plan_type = "Deep Dive"
        if commits_30d < 5:
            plan_type = "Micro-Learning"
            reasoning += " (Low activity detected. Adjusted to Micro-Learning: 15 min/day)."

        # 3. Check Hardcore Mode (Gamification Rule)
        # Rule: If streak >= 4 weeks, UNLOCK "HARDCORE MODE"
        is_hardcore = (user.streak_count or 0) >= 4
        if is_hardcore:
             focus_skill = "System Design"
             reasoning = "🔥 HARDCORE MODE ACTIVE: Streak >= 4. Tutorials disabled. Ruthless Challenges only."
             plan_type = "HARDCORE"

        # 4. Generate Routine
        week_id = datetime.datetime.now().strftime("%Y-W%U")

        if plan_type == "Micro-Learning":
            routine = [
                {"id": 1, "day": "Mon", "type": "Learn", "task": f"15 min: {focus_skill} Syntax", "status": "pending"},
                {"id": 2, "day": "Wed", "type": "Code", "task": f"Snippet: Hello World in {focus_skill}", "verify_key": focus_skill.lower(), "status": "pending"},
                {"id": 3, "day": "Fri", "type": "Review", "task": "Quick Quiz", "status": "pending"}
            ]
        elif plan_type == "HARDCORE":
             routine = [
                {"id": 1, "day": "Mon", "type": "Design", "task": "System Design: Distributed Rate Limiter", "status": "pending"},
                {"id": 2, "day": "Wed", "type": "Code", "task": "Implement Token Bucket Algo", "verify_key": focus_skill.lower(), "status": "pending"},
                {"id": 3, "day": "Fri", "type": "Code", "task": "Load Test & Benchmark", "verify_key": focus_skill.lower(), "status": "pending"}
             ]
        else:
             routine = [
                {"id": 1, "day": "Mon", "type": "Learn", "task": f"Deep Dive: {focus_skill} Core Concepts", "status": "pending"},
                {"id": 2, "day": "Wed", "type": "Code", "task": f"CLI Tool: Parse JSON in {focus_skill}", "verify_key": focus_skill.lower(), "status": "pending"},
                {"id": 3, "day": "Fri", "type": "Code", "task": f"Refactor: Optimize {focus_skill} Code", "verify_key": focus_skill.lower(), "status": "pending"}
            ]

        plan = {
            "week_id": week_id,
            "focus_language": focus_skill,
            "reasoning": reasoning,
            "routine": routine,
            "mode": plan_type
        }

        # Save to DB (WeeklyRoutine)
        wr = db.query(WeeklyRoutine).filter(WeeklyRoutine.user_id == user.id, WeeklyRoutine.week_id == week_id).first()
        if not wr:
            wr = WeeklyRoutine(
                user_id=user.id,
                week_id=week_id,
                mode=plan_type,
                focus=focus_skill,
                tasks=routine
            )
            db.add(wr)
        else:
            wr.mode = plan_type
            wr.focus = focus_skill
            wr.tasks = routine # Update tasks

        # Save to Profile
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

                 # Streak Logic using last_weekly_check
                 last_check = user.last_weekly_check
                 is_new_week = True

                 if last_check:
                      if last_check.isocalendar()[1] == now.isocalendar()[1] and last_check.year == now.year:
                           is_new_week = False

                 if is_new_week:
                      user.streak_count = (user.streak_count or 0) + 1
                      user.last_weekly_check = now
                      plan["last_verified_at"] = now.isoformat()

                 # UPDATE WeeklyRoutine
                 wr = db.query(WeeklyRoutine).filter(WeeklyRoutine.user_id == user_id, WeeklyRoutine.week_id == plan.get("week_id")).first()
                 if wr:
                     # Update the specific task in JSON
                     current_tasks = list(wr.tasks)
                     for t in current_tasks:
                         if t["id"] == task_id:
                             t["status"] = "completed"
                     wr.tasks = current_tasks # Trigger update

                     if all(t.get("status") == "completed" for t in current_tasks):
                         wr.completed = True
                         wr.completed_at = now

                 profile.active_weekly_plan = dict(plan)
                 db.commit()

                 return {"success": True, "message": "Task Verified! Streak Updated.", "task": task}
            else:
                 return {"success": False, "message": f"No code detected for {verify_key}. Push code to GitHub and try again."}

    def _check_plan_sync(self, user_id: int, db: Session) -> bool:
        u = db.query(User).filter(User.id == user_id).first()
        if u and u.career_profile and u.career_profile.active_weekly_plan:
            return True
        return False

    async def verify_task(self, db: Session, user: User, task_id: int) -> dict:
        """
        Triggers a SocialHarvester scan and checks if the task can be marked complete.
        """
        has_plan = await asyncio.to_thread(self._check_plan_sync, user.id, db)
        if not has_plan:
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
