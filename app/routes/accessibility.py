from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.core.templates import templates

from app.db.session import SessionLocal
from app.db.models.user import User
from app.core.jwt import decode_token
from app.services.onboarding import validate_onboarding_access
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user_optional(request: Request, db: Session) -> User | None:
    token = request.cookies.get("access_token")
    if not token:
        return None

    payload = decode_token(token)
    if not payload:
        return None

    user_id = int(payload.get("sub"))
    return db.query(User).filter(User.id == user_id).first()


@router.get("/accessibility", response_class=HTMLResponse)
def accessibility_panel(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)

    if user:
        # Authenticated User -> Dashboard View
        return templates.TemplateResponse(
            "accessibility.html",
            {
                "request": request,
                "user": user
            }
        )
    else:
        # Public User -> Public View
        return templates.TemplateResponse(
            "accessibility_public.html",
            {
                "request": request
            }
        )
