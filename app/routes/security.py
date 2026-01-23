from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models.user import User
from app.core.jwt import decode_token
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


@router.get("/dashboard/security", response_class=HTMLResponse)
def security_panel(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)

    # 🛡️ PROTEÇÃO ABSOLUTA: nunca acessar atributos se user for None
    if user is None:
        return RedirectResponse("/login", status_code=302)

    # GUARD: Ensure Onboarding is Complete
    if resp := validate_onboarding_access(user):
        return resp

    # Session Info
    user_agent = request.headers.get('user-agent', 'Unknown Device')
    client_ip = request.client.host if request.client else 'Unknown IP'

    return templates.TemplateResponse(
        "security.html",
        {
            "request": request,
            "no_user": False,
            "user": user,
            "current_session": {
                "user_agent": user_agent,
                "ip": client_ip
            }
        }
    )

@router.post("/dashboard/security/update")
def update_security(
    request: Request,
    db: Session = Depends(get_db)
):
    # This route previously updated language.
    # Now it does nothing or could update other preferences.
    # For now, we just redirect back.

    user = get_current_user(request, db)
    if not user:
         return RedirectResponse("/login", status_code=302)

    # GUARD: Ensure Onboarding is Complete
    if resp := validate_onboarding_access(user):
        return resp

    return RedirectResponse("/dashboard/security?success=true", status_code=302)

@router.post("/dashboard/security/delete-account")
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
