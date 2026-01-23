from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models.user import User
from app.core.jwt import decode_token
from app.i18n.loader import get_texts
from app.services.onboarding import validate_onboarding_access
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


@router.get("/dashboard/accessibility", response_class=HTMLResponse)
def accessibility_panel(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)

    # Protection
    if user is None:
        return RedirectResponse("/login", status_code=302)

    # GUARD: Ensure Onboarding is Complete
    if resp := validate_onboarding_access(user):
        return resp

    # Load Language
    lang = request.session.get("lang", user.preferred_language or "pt")
    t = get_texts(lang)

    return templates.TemplateResponse(
        "accessibility.html",
        {
            "request": request,
            "lang": lang,
            "t": t,
            "user": user
        }
    )
