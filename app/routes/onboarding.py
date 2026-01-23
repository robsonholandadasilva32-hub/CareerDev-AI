import asyncio
from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
import logging

from app.db.session import get_db
from app.db.models.user import User
from app.core.jwt import decode_token
from app.services.onboarding import get_next_onboarding_step
from app.services.security_service import log_audit

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

def get_current_user_onboarding(request: Request, db: Session = Depends(get_db)):
    # 🛡️ Relies on AuthMiddleware for session validation
    if not getattr(request.state, "user", None):
        return None
    # Re-query to attach to current db session
    return db.query(User).filter(User.id == request.state.user.id).first()

def redirect_to_dashboard():
    """Returns a non-cached redirect to dashboard."""
    response = RedirectResponse(url="/dashboard", status_code=303)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@router.get("/onboarding/connect-github", response_class=HTMLResponse)
async def connect_github(request: Request, user: User = Depends(get_current_user_onboarding)):
    if not user:
        return RedirectResponse("/login")

    # FORCE CHECK: Absolute Priority
    if user.is_profile_completed:
        logger.info(f"Onboarding Guard: User {user.id} is already completed. Redirecting to Dashboard.")
        return redirect_to_dashboard()

    # If already connected, move to next step
    if user.github_id:
        return RedirectResponse(get_next_onboarding_step(user))

    return templates.TemplateResponse("onboarding_github.html", {"request": request, "user": user})

@router.get("/onboarding/complete-profile", response_class=HTMLResponse)
async def complete_profile(request: Request, user: User = Depends(get_current_user_onboarding)):
    if not user:
        return RedirectResponse("/login")

    # FORCE CHECK: Absolute Priority
    if user.is_profile_completed:
        logger.info(f"Onboarding Guard: User {user.id} is already completed. Redirecting to Dashboard.")
        return redirect_to_dashboard()

    # Ensure pre-requisites
    if not user.linkedin_id:
         return RedirectResponse("/login")
    if not user.github_id:
         return RedirectResponse("/onboarding/connect-github")

    return templates.TemplateResponse("onboarding_profile.html", {"request": request, "user": user})

@router.post("/onboarding/complete-profile")
async def complete_profile_post(
    request: Request,
    name: str = Form(...),
    # Address fields removed or made optional (ignoring them if sent)
    terms_accepted: bool = Form(False),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_onboarding)
):
    if not user:
        return RedirectResponse("/login")

    # FORCE CHECK: Absolute Priority
    if user.is_profile_completed:
        return redirect_to_dashboard()

    if not terms_accepted:
        return templates.TemplateResponse("onboarding_profile.html", {
            "request": request,
            "user": user,
            "error": "You must read and accept the Terms of Use."
        })

    def save_profile():
        # Update User
        user.name = name

        # Address fields update logic removed

        user.terms_accepted = True
        user.terms_accepted_at = datetime.utcnow()
        user.is_profile_completed = True

        log_audit(db, user.id, "PROFILE_UPDATE", request.client.host, "Profile Completed via Onboarding")

        db.commit()

    await asyncio.to_thread(save_profile)

    return redirect_to_dashboard()
