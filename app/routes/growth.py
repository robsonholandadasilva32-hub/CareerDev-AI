from fastapi import APIRouter, Depends, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from pydantic import BaseModel

from app.db.session import get_db
from app.db.models.user import User
from app.services.social_harvester import social_harvester
from app.core.auth_guard import get_current_user_from_request

router = APIRouter()

class VerifyTaskRequest(BaseModel):
    task_id: int
    target_skill: str

@router.post("/verify")
async def verify_task(
    request: Request,
    body: VerifyTaskRequest,
    db: Session = Depends(get_db)
):
    """
    Verifies a Weekly Plan task by scanning GitHub.
    """
    user_id = get_current_user_from_request(request)
    if not user_id:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return JSONResponse({"error": "User not found"}, status_code=404)

    # 1. Trigger Live Scan (Await it for immediate feedback)
    if user.github_token:
        # Await the scan to get fresh data
        # Note: In production, this might be too slow for HTTP req,
        # but for this specific "Prove It" button, the user expects a loading state.
        try:
             await social_harvester.sync_profile(db, user, user.github_token)
        except Exception as e:
             return JSONResponse({"error": f"Scan failed: {str(e)}"}, status_code=500)
    else:
        # Fallback simulation for users without token
        await social_harvester.scan_github(db, user)

    # 2. Check Logic
    profile = user.career_profile
    plan = profile.active_weekly_plan

    if not plan:
        return JSONResponse({"error": "No active plan"}, status_code=400)

    # Find Task
    task = None
    routine = plan.get("routine", [])
    for t in routine:
        if t.get("id") == body.task_id:
            task = t
            break

    if not task:
        return JSONResponse({"error": "Task not found"}, status_code=404)

    # Verification Rule: Does the skill exist in GitHub now?
    metrics = profile.github_activity_metrics or {}
    raw_langs = metrics.get("raw_languages", {})

    # Normalize
    skill_key = body.target_skill.lower()
    user_skills = {k.lower(): v for k, v in raw_langs.items()}

    verified = False

    # Simple verification: If we found bytes for this skill, it's verified.
    # Logic: "Code: Create Rust CLI" -> We look for "Rust" in languages.
    if skill_key in user_skills and user_skills[skill_key] > 0:
        verified = True

    # Simulation Bypass (for demo purposes if specific header or dev env)
    # If using simulation harvest, it might not inject specific skills.
    # Let's be lenient for the MVP: If harvest succeeded, we mark as done.
    # BUT the prompt asks for specific verification.
    # "If verified..."

    if verified:
        # Update Task Status
        task["status"] = "completed"
        # Save updated plan
        profile.active_weekly_plan = plan # Trigger update

        # 3. Gamification: Streak Logic
        current_week = datetime.utcnow().strftime("%Y-W%U")
        last_check = user.last_weekly_check

        is_new_week_for_user = True
        if last_check:
             last_check_week = last_check.strftime("%Y-W%U")
             if last_check_week == current_week:
                 is_new_week_for_user = False

        if is_new_week_for_user:
            user.weekly_streak_count = (user.weekly_streak_count or 0) + 1
            user.last_weekly_check = datetime.utcnow()

        db.commit()

        return {
            "status": "success",
            "verified": True,
            "message": f"Verified {body.target_skill} code! Streak updated.",
            "new_streak": user.weekly_streak_count
        }

    else:
        return JSONResponse({
            "status": "failed",
            "verified": False,
            "message": f"Could not find new {body.target_skill} code in your recent GitHub activity."
        }, status_code=200) # 200 OK but logical failure
