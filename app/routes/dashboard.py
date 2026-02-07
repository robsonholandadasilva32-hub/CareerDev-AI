from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import logging
import asyncio

from app.core.jwt import decode_token
from app.services.career_engine import career_engine
from app.services.social_harvester import social_harvester
from app.services.growth_engine import growth_engine
from app.services.github_verifier import github_verifier
from app.services.onboarding import validate_onboarding_access
from app.services.security_service import get_active_sessions, revoke_session, log_audit
from app.db.session import get_db, SessionLocal
from app.db.models.user import User
from app.db.models.security import UserSession
from app.core.dependencies import get_user_with_profile
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# -------------------------------------------------
# DASHBOARD
# -------------------------------------------------
@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_user_with_profile)
):
    if not user:
        return RedirectResponse("/login", status_code=302)

    redirect = validate_onboarding_access(user)
    if redirect:
        return redirect

    # Atualiza / recalcula dados de carreira
    profile = user.career_profile
    raw_languages = profile.github_activity_metrics.get("raw_languages", {}) if profile and profile.github_activity_metrics else {}
    linkedin_input = profile.linkedin_alignment_data or {} if profile else {}
    metrics = profile.github_activity_metrics or {} if profile else {}
    skill_audit = profile.skills_graph_data or {} if profile else {}

    # Optimization Verified: Wrapped in asyncio.to_thread to prevent event loop blocking
    career_data = await asyncio.to_thread(
        career_engine.analyze,
        db=db,
        raw_languages=raw_languages,
        linkedin_input=linkedin_input,
        metrics=metrics,
        skill_audit=skill_audit,
        user=user
    )

    # Patch Missing Data for Dashboard
    if not career_data.get("zone_a_radar"):
        career_data["zone_a_radar"] = skill_audit

    if not career_data.get("zone_a_holistic"):
        career_data["zone_a_holistic"] = {"score": profile.market_relevance_score if profile else 0}

    # >>> ADIÇÃO AQUI <<<
    weekly_history = await career_engine.get_weekly_history(db, user)

    market_score = career_data.get("zone_a_holistic", {}).get("score", 0)
    user_streak = getattr(user, "streak_count", 0)

    greeting_message = "Hello! Ready to optimize your career?"

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user,
            "market_score": market_score,
            "user_streak": user_streak,
            "career_data": career_data,
            "weekly_history": weekly_history,  # ✅ NOVO
            "greeting_message": greeting_message,
        }
    )


def _update_streak_sync(user_id: int):
    """
    Helper to update user streak in a thread-safe dedicated session.
    """
    with SessionLocal() as db:
        # Re-fetch user to avoid attaching detached objects to new session
        u = db.query(User).filter(User.id == user_id).first()
        if u:
            u.streak_count = (u.streak_count or 0) + 1
            db.commit()


def _update_last_weekly_check_sync(user_id: int):
    """
    Helper to update last_weekly_check in a thread-safe dedicated session.
    """
    with SessionLocal() as db:
        u = db.query(User).filter(User.id == user_id).first()
        if u:
            # Use timezone-aware datetime
            u.last_weekly_check = datetime.now(timezone.utc)
            db.commit()
            return u.last_weekly_check
    return None

# -------------------------------------------------
# API REAL: VERIFICAÇÃO DE CÓDIGO
# -------------------------------------------------
@router.post("/api/verify/repo", response_class=JSONResponse)
async def verify_repo(
    payload: dict,
    db: Session = Depends(get_db),
    user: User = Depends(get_user_with_profile)
):
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    language = payload.get("language")
    if not language:
        raise HTTPException(status_code=400, detail="Language not provided")

    # 1. Offload Blocking Network Call (PyGithub is synchronous)
    # We pass the user's token (if available) to increase API limits
    commits = await asyncio.to_thread(
        social_harvester.get_recent_commits,
        user.github_username,
        user.github_token
    )

    verified = github_verifier.verify(commits, language)

    if verified:
        # 2. Offload Blocking DB Commit
        # We use a dedicated sync helper with its own session to ensure thread safety
        await asyncio.to_thread(_update_streak_sync, user.id)

    return {"verified": verified}
    
    # -------------------------------------------------
# ROTA PARA WEEKLY CHECK-IN (Adicione isso!)
# -------------------------------------------------
@router.post("/api/dashboard/weekly-check")
async def perform_weekly_check(
    db: Session = Depends(get_db),
    user: User = Depends(get_user_with_profile)
):
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Offload Blocking DB Commit
    timestamp = await asyncio.to_thread(_update_last_weekly_check_sync, user.id)
    
    if not timestamp:
         raise HTTPException(status_code=404, detail="User not found")

    return {"status": "success", "timestamp": timestamp.isoformat()}

# -------------------------------------------------
# KANBAN TASK VERIFICATION API
# -------------------------------------------------
@router.post("/api/verify/task/{task_id}")
async def verify_task_endpoint(
    task_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_user_with_profile)
):
    """
    Verifies a specific task from the Weekly Plan (Kanban).
    """
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    result = await growth_engine.verify_task(db, user, task_id)
    return result
