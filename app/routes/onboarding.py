import asyncio
from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime

from app.db.session import get_db
from app.db.models.user import User
from app.core.jwt import decode_token
from app.services.onboarding import get_next_onboarding_step
from app.services.security_service import log_audit

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

def get_current_user_onboarding(request: Request, db: Session = Depends(get_db)):
    # 🛡️ Relies on AuthMiddleware for session validation
    if not getattr(request.state, "user", None):
        return None
    # Re-query to attach to current db session
    return db.query(User).filter(User.id == request.state.user.id).first()

@router.get("/onboarding/connect-github", response_class=HTMLResponse)
async def connect_github(request: Request, user: User = Depends(get_current_user_onboarding)):
    # FORCE CHECK: If profile is completed, DO NOT allow access to onboarding routes
    if user.is_profile_completed:
        print(f"DEBUG: User {user.id} is completed. Forcing redirect to Dashboard.")
        return RedirectResponse(url="/dashboard", status_code=303)

    if not user:
        return RedirectResponse("/login")

    # If already connected, move to next step
    if user.github_id:
        return RedirectResponse(get_next_onboarding_step(user))

    return templates.TemplateResponse("onboarding_github.html", {"request": request, "user": user})

@router.get("/onboarding/complete-profile", response_class=HTMLResponse)
async def complete_profile(request: Request, user: User = Depends(get_current_user_onboarding)):
    # FORCE CHECK: If profile is completed, DO NOT allow access to onboarding routes
    if user.is_profile_completed:
        print(f"DEBUG: User {user.id} is completed. Forcing redirect to Dashboard.")
        return RedirectResponse(url="/dashboard", status_code=303)

    if not user:
        return RedirectResponse("/login")

    next_step = get_next_onboarding_step(user)

    # Simple check:
    if not user.linkedin_id:
        return RedirectResponse("/login") # Should not happen if logged in usually
    if not user.github_id:
         return RedirectResponse("/onboarding/connect-github")

    if user.is_profile_completed:
         return RedirectResponse("/dashboard")

    return templates.TemplateResponse("onboarding_profile.html", {"request": request, "user": user})

@router.post("/onboarding/complete-profile")
async def complete_profile_post(
    request: Request,
    name: str = Form(...),
    address_street: str = Form(...),
    address_number: str = Form(...),
    address_complement: str = Form(None),
    address_city: str = Form(...),
    address_state: str = Form(...),
    address_zip_code: str = Form(...),
    address_country: str = Form(...),

    billing_same_as_residential: bool = Form(False),

    billing_address_street: str = Form(None),
    billing_address_number: str = Form(None),
    billing_address_complement: str = Form(None),
    billing_address_city: str = Form(None),
    billing_address_state: str = Form(None),
    billing_address_zip_code: str = Form(None),
    billing_address_country: str = Form(None),

    terms_accepted: bool = Form(False),

    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_onboarding)
):
    # FORCE CHECK: If profile is completed, DO NOT allow access to onboarding routes
    if user.is_profile_completed:
        print(f"DEBUG: User {user.id} is completed. Forcing redirect to Dashboard.")
        return RedirectResponse(url="/dashboard", status_code=303)

    if not user:
        return RedirectResponse("/login")

    if not terms_accepted:
        return templates.TemplateResponse("onboarding_profile.html", {
            "request": request,
            "user": user,
            "error": "You must read and accept the Terms of Use."
        })

    # Update User
    user.name = name

    # Residential
    user.address_street = address_street
    user.address_number = address_number
    user.address_complement = address_complement
    user.address_city = address_city
    user.address_state = address_state
    user.address_zip_code = address_zip_code
    user.address_country = address_country

    # Billing
    if billing_same_as_residential:
        user.billing_address_street = address_street
        user.billing_address_number = address_number
        user.billing_address_complement = address_complement
        user.billing_address_city = address_city
        user.billing_address_state = address_state
        user.billing_address_zip_code = address_zip_code
        user.billing_address_country = address_country
    else:
        # Validate billing fields if not same
        if not all([billing_address_street, billing_address_number, billing_address_city, billing_address_state, billing_address_zip_code, billing_address_country]):
             return templates.TemplateResponse("onboarding_profile.html", {
                "request": request,
                "user": user,
                "error": "Please fill in all billing address fields or check 'Same as residential'."
            })

        user.billing_address_street = billing_address_street
        user.billing_address_number = billing_address_number
        user.billing_address_complement = billing_address_complement
        user.billing_address_city = billing_address_city
        user.billing_address_state = billing_address_state
        user.billing_address_zip_code = billing_address_zip_code
        user.billing_address_country = billing_address_country

    user.terms_accepted = True
    user.terms_accepted_at = datetime.utcnow()
    user.is_profile_completed = True

    log_audit(db, user.id, "PROFILE_UPDATE", request.client.host, "Profile Completed via Onboarding")

    db.commit()

    return RedirectResponse("/dashboard", status_code=302)
