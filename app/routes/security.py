from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models.user import User
from app.core.jwt import decode_token

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

    return templates.TemplateResponse(
        "security.html",
        {
            "request": request,
            "two_factor_enabled": bool(user.two_factor_enabled),
            "two_factor_method": user.two_factor_method,
            "user_phone": user.phone_number, # Pass phone to template
            "no_user": False
        }
    )

@router.post("/security/update")
def update_security(
    request: Request,
    method: str = Form("email"),
    phone: str = Form(None),
    contact_dev: str = Form(None),
    message_body: str = Form(None),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)

    if not user:
         return RedirectResponse("/login", status_code=302)

    # 1. Update 2FA Settings
    user.two_factor_method = method
    if phone:
        user.phone_number = phone

    # "Intelligent Fallback" logic is implied in the Notification Service (not here),
    # but we ensure we have the data.

    # 2. Contact Developer Feature
    if contact_dev == "true" and message_body:
        from app.services.notifications import send_email
        # Attempt to send real email if configured, else log
        subject = f"Support Request from {user.email}: {user.name}"
        try:
             send_email(to="robsonholandasilva@yahoo.com.br", subject=subject, body=message_body)
             print(f"📧 [SUPPORT] Sent email to developer from {user.email}")
        except Exception as e:
             print(f"📧 [SUPPORT ERROR] Could not send email: {e}")
             # Fallback log
             print(f"📧 [SUPPORT CONTENT] {message_body}")

    db.commit()
    return RedirectResponse("/security?success=true", status_code=302)
