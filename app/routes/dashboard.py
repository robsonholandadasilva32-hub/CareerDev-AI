from fastapi import APIRouter, Request, Depends, HTTPException, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload

from app.core.jwt import decode_token
from app.services.career_engine import career_engine
from app.services.social_harvester import social_harvester
from app.services.onboarding import validate_onboarding_access
from app.services.security_service import get_active_sessions, revoke_session, log_audit
from app.db.session import get_db
from app.db.models.user import User
from app.db.models.security import UserSession
from app.db.models.gamification import UserBadge

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def get_current_user_secure(request: Request, db: Session = Depends(get_db)):
    # 🛡️ Relies on AuthMiddleware for session validation
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

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user_secure)):
    # 1️⃣ Secure Auth Dependency Check
    if not user:
        return RedirectResponse("/login", status_code=302)

    # CRITICAL ARCHITECTURE CHANGE: Strict Sequential Flow
    redirect = validate_onboarding_access(user)
    if redirect:
        return redirect

    user_id = user.id
    email = user.email

    # 3️⃣ Career Data (Real Logic)
    # This will create/update the profile and sync (simulated) external data
    profile_data = career_engine.analyze_profile(db, user)

    # Generate/Fetch Plan
    plan_items = career_engine.generate_plan(db, user)

    # New AI Brain Data
    career_data = career_engine.get_career_dashboard_data(db, user)

    # 5️⃣ Renderiza o dashboard
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user,
            "user_id": user_id,
            "email": email,
            "profile": profile_data,
            "plan": plan_items, # List of LearningPlan objects
            "badges": user.badges, # Pass UserBadges to template
            "career_data": career_data, # NEW
        }
    )

@router.get("/api/dashboard/stats", response_class=JSONResponse)
def get_dashboard_stats(user: User = Depends(get_current_user_secure), db: Session = Depends(get_db)):
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    data = career_engine.get_career_dashboard_data(db, user)
    return data

@router.post("/api/dashboard/complete-task/{task_id}", response_class=JSONResponse)
def complete_task(task_id: int, background_tasks: BackgroundTasks, user: User = Depends(get_current_user_secure), db: Session = Depends(get_db)):
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    profile = user.career_profile
    if not profile or not profile.pending_micro_projects:
        return JSONResponse({"error": "No tasks found"}, status_code=404)

    # Update Status
    tasks = list(profile.pending_micro_projects)
    updated = False
    for t in tasks:
        if t.get("id") == task_id:
            t["status"] = "completed"
            updated = True
            break

    if updated:
        # Re-assign to trigger SQLAlchemy detection of change
        profile.pending_micro_projects = tasks

        # Simulate Score Boost (Immediate UI feedback)
        if profile.market_relevance_score is None:
            profile.market_relevance_score = 0
        if profile.market_relevance_score < 100:
             profile.market_relevance_score += 5

        db.commit()

        # Phase 4 Requirement: Trigger SocialDataService.scan_github()
        # "scan_github" is the verification logic
        background_tasks.add_task(social_harvester.scan_github, db, user)

    data = career_engine.get_career_dashboard_data(db, user)
    return data

# ==========================================
# NOVAS ROTAS DE SEGURANÇA (Da Feature Branch)
# MOVED TO app/routes/security.py
# ==========================================


# ==========================================
# NOVAS ROTAS LEGAIS (Da Main Branch)
# ==========================================

@router.get("/dashboard/legal", response_class=HTMLResponse)
def dashboard_legal(request: Request, user: User = Depends(get_current_user_secure)):
    if not user:
        return RedirectResponse("/login", status_code=302)

    # GUARD (REMOVED)
    return templates.TemplateResponse(
        "legal_menu.html",
        {
            "request": request,
            "user": user,
        }
    )
