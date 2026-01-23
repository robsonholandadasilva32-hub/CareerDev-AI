from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload

from app.core.jwt import decode_token
from app.services.career_engine import career_engine
from app.services.onboarding import validate_onboarding_access
from app.services.security_service import get_active_sessions, revoke_session, log_audit
from app.db.session import get_db
from app.db.models.user import User
from app.db.models.security import UserSession
from app.db.models.gamification import UserBadge
from app.middleware.subscription import check_subscription_status

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def get_current_user_secure(request: Request, db: Session = Depends(get_db)):
    # 🛡️ Relies on AuthMiddleware for session validation
    if not getattr(request.state, "user", None):
        return None

    user_id = request.state.user.id
    user = (
        db.query(User)
        .options(joinedload(User.badges).joinedload(UserBadge.badge))
        .filter(User.id == user_id)
        .first()
    )
    return user

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user_secure)):
    # 1️⃣ Secure Auth Dependency Check
    if not user:
        return RedirectResponse("/login", status_code=302)

    # GUARD: Ensure Onboarding is Complete
    if resp := validate_onboarding_access(user):
        return resp

    user_id = user.id
    email = user.email

    # 2.5️⃣ Check Subscription Status
    is_allowed = check_subscription_status(user)
    if not is_allowed:
            # Redirect to Billing if trial expired
            return RedirectResponse("/billing", status_code=302)

    # 3️⃣ Career Data (Real Logic)
    # This will create/update the profile and sync (simulated) external data
    profile_data = career_engine.analyze_profile(db, user)

    # Generate/Fetch Plan
    plan_items = career_engine.generate_plan(db, user)

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
        }
    )

# ==========================================
# NOVAS ROTAS DE SEGURANÇA (Da Feature Branch)
# ==========================================

@router.get("/dashboard/security", response_class=HTMLResponse)
def dashboard_security(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user_secure)):
    if not user:
        return RedirectResponse("/login")

    sessions = get_active_sessions(db, user.id)

    # Identify current session
    token = request.cookies.get("access_token")
    current_sid = None
    if token:
        payload = decode_token(token)
        if payload:
            current_sid = payload.get("sid")

    return templates.TemplateResponse("dashboard/security.html", {
        "request": request,
        "user": user,
        "sessions": sessions,
        "current_sid": current_sid,
    })

@router.post("/dashboard/security/revoke/{session_id}")
def revoke_user_session_route(session_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user_secure)):
    if not user:
        return RedirectResponse("/login")

    # Security: Ensure session belongs to user
    session_to_revoke = db.query(UserSession).filter(UserSession.id == session_id, UserSession.user_id == user.id).first()
    if session_to_revoke:
        revoke_session(db, session_id)
        log_audit(db, user.id, "REVOKE_SESSION", request.client.host, f"Revoked session {session_id}")

    return RedirectResponse("/dashboard/security", status_code=303)

# ==========================================
# NOVAS ROTAS LEGAIS (Da Main Branch)
# ==========================================

@router.get("/dashboard/legal", response_class=HTMLResponse)
def dashboard_legal(request: Request, user: User = Depends(get_current_user_secure)):
    if not user:
        return RedirectResponse("/login", status_code=302)

    # GUARD
    if resp := validate_onboarding_access(user):
        return resp

    return templates.TemplateResponse(
        "legal_menu.html",
        {
            "request": request,
            "user": user,
        }
    )
