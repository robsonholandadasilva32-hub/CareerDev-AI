from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models.user import User
from app.core.jwt import decode_token, create_access_token
from app.i18n.loader import get_texts
from app.core.security import verify_password, hash_password
from app.services.notifications import enqueue_email, enqueue_telegram, create_otp, verify_otp
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

    # 2. Password Change Interception (Security Check)
    if current_password and new_password:
        if verify_password(current_password, user.hashed_password):
            if new_password == confirm_password:
                # 🛑 DO NOT UPDATE YET. Require 2FA.
                method = user.two_factor_method or "email"
                create_otp(db, user.id, method)

                # Create temporary token to store new password hash securely
                new_hash = hash_password(new_password)
                security_temp_token = create_access_token({
                    "sub": str(user.id),
                    "new_hash": new_hash,
                    "change_type": "password"
                }, expires_minutes=10)

                response = RedirectResponse("/security/verify-change", status_code=302)
                response.set_cookie(
                    key="security_temp_token",
                    value=security_temp_token,
                    httponly=True,
                    secure=request.url.scheme == "https",
                    samesite="lax"
                )

                # Commit other changes (profile/language) before redirecting?
                # For simplicity, we commit profile changes now. Password change is deferred.
                db.commit()
                return response
            else:
                return RedirectResponse("/security?error=password_mismatch", status_code=302)
        else:
            return RedirectResponse("/security?error=invalid_password", status_code=302)

    password_changed = False # Placeholder for legacy logic below

    # 3. Contact Developer Feature
    if contact_dev == "true" and message_body:
        from app.services.notifications import enqueue_raw_email
        subject = f"Support Request from {user.email}: {user.name}"
        try:
             enqueue_raw_email(db, settings.ADMIN_EMAIL, subject, message_body)
        except Exception as e:
             logger.error(f"SUPPORT ERROR: Could not enqueue email: {e}")

    db.commit()

    # Trigger Emails & Telegram
    t = get_texts(language) # Ensure we have texts for keys

    # Send independent notifications for each distinct type of change
    # Note: Password change notification is now handled in verify_change
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

# =====================================================
# SECURITY CHANGE VERIFICATION (GET)
# =====================================================
@router.get("/security/verify-change", response_class=HTMLResponse)
def verify_security_change_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)

    lang = request.query_params.get("lang", user.preferred_language or "pt")
    t = get_texts(lang)

    return templates.TemplateResponse(
        "verify_2fa.html",
        {
            "request": request,
            "lang": lang,
            "t": t,
            "page_title": "Verificação de Alteração",
            "instructions": "Para sua segurança, confirme a alteração sensível na sua conta.",
            "form_action": "/security/verify-change",
            "resend_action": "/security/resend-change"
        }
    )

# =====================================================
# SECURITY CHANGE RESEND (POST)
# =====================================================
@router.post("/security/resend-change")
def resend_security_change(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)

    security_temp_token = request.cookies.get("security_temp_token")
    if not security_temp_token:
        return RedirectResponse("/security", status_code=302)

    # Validate token existence/format (logic similar to verify)
    payload = decode_token(security_temp_token)
    if not payload or str(payload.get("sub")) != str(user.id):
        return RedirectResponse("/security", status_code=302)

    method = user.two_factor_method or "email"
    create_otp(db, user.id, method)

    return RedirectResponse("/security/verify-change", status_code=302)

# =====================================================
# SECURITY CHANGE VERIFICATION (POST)
# =====================================================
@router.post("/security/verify-change")
def verify_security_change(
    request: Request,
    code: str = Form(...),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)

    lang = user.preferred_language or "pt"
    t = get_texts(lang)

    security_temp_token = request.cookies.get("security_temp_token")
    if not security_temp_token:
        return RedirectResponse("/security?error=session_expired", status_code=302)

    payload = decode_token(security_temp_token)
    if not payload or str(payload.get("sub")) != str(user.id):
        return RedirectResponse("/security?error=invalid_session", status_code=302)

    # Verify OTP
    if verify_otp(db, user.id, code):
        change_type = payload.get("change_type")

        if change_type == "password":
            new_hash = payload.get("new_hash")
            user.hashed_password = new_hash
            db.commit()

            # Notify
            enqueue_email(db, user.id, "account_update", {"change_type": "password"})
            enqueue_telegram(db, user.id, "telegram_security_alert", {"change_desc": t.get("telegram_update_password", "Password changed")})

        response = RedirectResponse("/security?success=true", status_code=302)
        response.delete_cookie("security_temp_token")
        return response

    return templates.TemplateResponse(
        "verify_2fa.html",
        {
            "request": request,
            "lang": lang,
            "t": t,
            "page_title": "Verificação de Alteração",
            "instructions": "Para sua segurança, confirme a alteração sensível na sua conta.",
            "form_action": "/security/verify-change",
            "resend_action": "/security/resend-change",
            "error": t.get("error_invalid_code", "Invalid code")
        }
    )
