from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models.user import User
from app.core.jwt import decode_token
from app.i18n.loader import get_texts
from app.services.onboarding import validate_onboarding_access
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(request: Request, db: Session) -> User | None:
    token = request.cookies.get("access_token")
    if not token:
        return None

    payload = decode_token(token)
    if not payload:
        return None

    user_id = int(payload.get("sub"))
    return db.query(User).filter(User.id == user_id).first()


@router.get("/security", response_class=HTMLResponse)
def security_panel(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)

    # 🛡️ PROTEÇÃO ABSOLUTA: nunca acessar atributos se user for None
    if user is None:
        return RedirectResponse("/login", status_code=302)

    # GUARD: Ensure Onboarding is Complete
    if resp := validate_onboarding_access(user):
        return resp

    # Load Language
    lang = request.session.get("lang", user.preferred_language or "pt")
    t = get_texts(lang)

    return templates.TemplateResponse(
        "security.html",
        {
            "request": request,
            "no_user": False,
            "lang": lang,
            "t": t,
            "user": user
        }
    )

@router.post("/security/update")
def update_security(
    request: Request,
    language: str = Form("pt"),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)

    if not user:
         return RedirectResponse("/login", status_code=302)

    # GUARD: Ensure Onboarding is Complete
    if resp := validate_onboarding_access(user):
        return resp

    # 1. Update Preferences
    if user.preferred_language != language:
        user.preferred_language = language
        request.session["lang"] = language # Update session immediately

    db.commit()

    return RedirectResponse("/security?success=true", status_code=302)

@router.post("/security/delete-account")
def delete_account(
    request: Request,
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)

    # No notifications sent.

    # Delete User (Cascade deletes profile/plans due to relationship config)
    db.delete(user)
    db.commit()

    # Logout
    response = RedirectResponse("/login?msg=account_deleted", status_code=302)
    response.delete_cookie("access_token")
    return response
