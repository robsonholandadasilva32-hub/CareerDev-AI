from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
import logging

from app.core.jwt import decode_token
from app.services.career_engine import career_engine
from app.services.social_harvester import social_harvester
from app.services.github_verifier import github_verifier
from app.services.onboarding import validate_onboarding_access
from app.services.security_service import get_active_sessions, revoke_session, log_audit
from app.db.session import get_db
from app.db.models.user import User
from app.db.models.security import UserSession
from app.db.models.gamification import UserBadge

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# -------------------------------------------------
# DEPENDÊNCIA DE SEGURANÇA
# -------------------------------------------------
def get_current_user_secure(
    request: Request,
    db: Session = Depends(get_db)
):
    if not getattr(request.state, "user", None):
        return None

    user_id = request.state.user.id

    user = (
        db.query(User)
        .options(
            joinedload(User.badges).joinedload(UserBadge.badge),
            joinedload(User.career_profile)
        )
        .filter(User.id == user_id)
        .first()
    )
    return user


# -------------------------------------------------
# DASHBOARD
# -------------------------------------------------
@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_secure)
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

    career_data = career_engine.analyze(
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


# -------------------------------------------------
# API REAL: VERIFICAÇÃO DE CÓDIGO
# -------------------------------------------------
@router.post("/api/verify/repo", response_class=JSONResponse)
async def verify_repo(
    payload: dict,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_secure)
):
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    language = payload.get("language")
    if not language:
        raise HTTPException(status_code=400, detail="Language not provided")

    commits = social_harvester.get_recent_commits(user.github_username)
    verified = github_verifier.verify(commits, language)

    if verified:
        user.streak_count = (user.streak_count or 0) + 1
        db.commit()

    return {"verified": verified}
