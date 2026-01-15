from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models.user import User
from app.core.jwt import decode_token
from app.i18n.loader import get_texts
from app.core.security import verify_password, hash_password
from app.services.notifications import enqueue_email, enqueue_telegram

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

    # Load Language
    lang = request.session.get("lang", user.preferred_language or "pt")
    t = get_texts(lang)

    return templates.TemplateResponse(
        "security.html",
        {
            "request": request,
            "two_factor_enabled": bool(user.two_factor_enabled),
            "two_factor_method": user.two_factor_method,
            "user_phone": user.phone_number, # Pass phone to template
            "no_user": False,
            "lang": lang,
            "t": t,
            "user": user # Pass full user object for base template checks (like trial banner)
        }
    )

@router.post("/security/update")
def update_security(
    request: Request,
    method: str = Form("email"),
    phone: str = Form(None), # Stores Telegram Chat ID now
    language: str = Form("pt"),
    current_password: str = Form(None),
    new_password: str = Form(None),
    confirm_password: str = Form(None),
    contact_dev: str = Form(None),
    message_body: str = Form(None),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)

    if not user:
         return RedirectResponse("/login", status_code=302)

    # 1. Update Preferences
    changes = []

    if user.two_factor_method != method:
        changes.append("2fa")
    user.two_factor_method = method

    if user.preferred_language != language:
        changes.append("profile")
    user.preferred_language = language
    request.session["lang"] = language # Update session immediately

    if phone and user.phone_number != phone:
        user.phone_number = phone
        changes.append("profile")

    # 2. Password Change
    password_changed = False
    if current_password and new_password:
        if verify_password(current_password, user.hashed_password):
            if new_password == confirm_password:
                user.hashed_password = hash_password(new_password)
                password_changed = True
                print(f"🔐 [SECURITY] Password updated for {user.email}")
            else:
                return RedirectResponse("/security?error=password_mismatch", status_code=302)
        else:
            return RedirectResponse("/security?error=invalid_password", status_code=302)

    # 3. Contact Developer Feature
    if contact_dev == "true" and message_body:
        from app.services.notifications import send_email
        subject = f"Support Request from {user.email}: {user.name}"
        try:
             send_email(to="robsonholandasilva@yahoo.com.br", subject=subject, body=message_body)
        except Exception as e:
             print(f"📧 [SUPPORT ERROR] Could not send email: {e}")

    db.commit()

    # Trigger Emails & Telegram
    t = get_texts(language) # Ensure we have texts for keys

    # Send independent notifications for each distinct type of change
    if password_changed:
        enqueue_email(db, user.id, "account_update", {"change_type": "password"})
        enqueue_telegram(db, user.id, "telegram_security_alert", {"change_desc": t.get("telegram_update_password", "Password changed")})

    if "2fa" in changes:
        enqueue_email(db, user.id, "account_update", {"change_type": "2fa"})
        enqueue_telegram(db, user.id, "telegram_security_alert", {"change_desc": t.get("telegram_update_2fa", "2FA updated")})

    if "profile" in changes:
        enqueue_email(db, user.id, "account_update", {"change_type": "profile"})
        enqueue_telegram(db, user.id, "telegram_security_alert", {"change_desc": t.get("telegram_update_profile", "Profile updated")})

    return RedirectResponse("/security?success=true", status_code=302)

@router.post("/security/delete-account")
def delete_account(
    request: Request,
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)

    # Notify before deletion
    t = get_texts(user.preferred_language or "pt")
    enqueue_email(db, user.id, "account_update", {"change_type": "account_deleted"})
    enqueue_telegram(db, user.id, "telegram_security_alert", {"change_desc": t.get("telegram_update_account_deleted", "Account deleted")})

    # Delete User (Cascade deletes profile/plans due to relationship config)
    db.delete(user)
    db.commit()

    # Logout
    response = RedirectResponse("/login?msg=account_deleted", status_code=302)
    response.delete_cookie("access_token")
    return response
