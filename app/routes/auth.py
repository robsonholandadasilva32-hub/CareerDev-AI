import asyncio
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.i18n.loader import get_texts
from app.core.security import verify_password, hash_password
from app.core.jwt import create_access_token
from app.db.crud.users import get_user_by_email, create_user
from app.db.crud.email_verification import create_email_verification
from app.db.session import get_db, SessionLocal
from app.services.notifications import create_otp, enqueue_email, enqueue_telegram, verify_otp
from app.core.limiter import limiter
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

MAX_LOGIN_ATTEMPTS = 3
LOCKOUT_TIME_MINUTES = 15

# =====================================================
# LOGIN PAGE (GET)
# =====================================================
@router.get("/", response_class=HTMLResponse)
@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    lang = request.query_params.get("lang")

    if lang not in ("pt", "en", "es", "fr", "de"):
        lang = request.session.get("lang", "pt")

    request.session["lang"] = lang
    t = get_texts(lang)

    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "lang": lang,
            "t": t
        }
    )

# =====================================================
# LOGIN (POST)
# =====================================================
@router.post("/login", response_class=HTMLResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    lang: str = Form("pt"),
    db: Session = Depends(get_db)
):
    t = get_texts(lang)

    user = get_user_by_email(db, email)

    if not user:
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "lang": lang,
                "t": t,
                "error": t["error_user_not_found"]
            }
        )

    # Check for Lockout
    if user.locked_until and user.locked_until > datetime.utcnow():
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "lang": lang,
                "t": t,
                "error": t.get("error_account_locked", "Account locked due to too many failed attempts. Try again later.")
            }
        )

    if not verify_password(password, user.hashed_password):
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1

        if user.failed_login_attempts >= MAX_LOGIN_ATTEMPTS:
            user.locked_until = datetime.utcnow() + timedelta(minutes=LOCKOUT_TIME_MINUTES)
            db.commit()
            return templates.TemplateResponse(
                "login.html",
                {
                    "request": request,
                    "lang": lang,
                    "t": t,
                    "error": t.get("error_account_locked_now", f"Too many failed attempts. Account locked for {LOCKOUT_TIME_MINUTES} minutes.")
                }
            )

        db.commit()
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "lang": lang,
                "t": t,
                "error": t["error_invalid_password"]
            }
        )

    # Successful login: Reset attempts
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()
        
    if not user.email_verified:
        return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "lang": lang,
            "t": t,
            "error": t.get(
            "error_email_not_verified",
            "Confirme seu e-mail para continuar"
            )
        }
    )

    # 🔐 Mandatory 2FA Check
    # Force 2FA for everyone (defaulting to email if not set)
    method = user.two_factor_method or "email"
    create_otp(db, user.id, method)

    # Temporary token for 2FA verification page
    # Short expiry (5 mins) for security
    temp_token = create_access_token({
        "sub": str(user.id),
        "email": user.email,
        "pre_2fa": True
    }, expires_minutes=5)

    response = RedirectResponse(f"/verify-2fa?lang={lang}", status_code=302)
    response.set_cookie(
        key="temp_token",
        value=temp_token,
        httponly=True,
        secure=request.url.scheme == "https", # Auto-detect HTTPS
        samesite="lax"
    )
    return response

# =====================================================
# FORGOT PASSWORD (GET)
# =====================================================
@router.get("/forgot-password", response_class=HTMLResponse)
def forgot_password_page(request: Request):
    lang = request.query_params.get("lang", "pt")
    if lang not in ("pt", "en", "es", "fr", "de"):
        lang = "pt"

    t = get_texts(lang)
    return templates.TemplateResponse(
        "forgot_password.html",
        {"request": request, "lang": lang, "t": t}
    )

# =====================================================
# FORGOT PASSWORD (POST)
# =====================================================
@router.post("/forgot-password", response_class=HTMLResponse)
@limiter.limit("3/minute")
async def forgot_password(
    request: Request,
    email: str = Form(...),
    lang: str = Form("pt")
):
    await asyncio.to_thread(_handle_forgot_password_db, email)

    return RedirectResponse(
        url=f"/reset-password?email={email}&lang={lang}",
        status_code=302
    )

def _handle_forgot_password_db(email: str):
    """Synchronous helper to avoid blocking the event loop."""
    db: Session = SessionLocal()
    try:
        user = get_user_by_email(db, email)
        if user:
            method = user.two_factor_method or "email"
            create_otp(
                db=db,
                user_id=user.id,
                method=method,
                template_name="password_reset",
                telegram_template_key="telegram_reset_message"
            )
    finally:
        db.close()

# =====================================================
# RESET PASSWORD (GET)
# =====================================================
@router.get("/reset-password", response_class=HTMLResponse)
def reset_password_page(request: Request):
    lang = request.query_params.get("lang", "pt")
    email = request.query_params.get("email", "")

    if lang not in ("pt", "en", "es", "fr", "de"):
        lang = "pt"

    t = get_texts(lang)
    return templates.TemplateResponse(
        "reset_password.html",
        {"request": request, "lang": lang, "t": t, "email": email}
    )

# =====================================================
# RESET PASSWORD (POST)
# =====================================================
@router.post("/reset-password", response_class=HTMLResponse)
@limiter.limit("5/minute")
async def reset_password(
    request: Request,
    email: str = Form(...),
    code: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    lang: str = Form("pt"),
    db: Session = Depends(get_db)
):
    t = get_texts(lang)

    # 1. Check passwords match
    if new_password != confirm_password:
        return templates.TemplateResponse(
            "reset_password.html",
            {
                "request": request,
                "lang": lang,
                "t": t,
                "email": email,
                "error": "Passwords do not match."
            }
        )

    # 2. Check User
    user = get_user_by_email(db, email)
    if not user:
        return templates.TemplateResponse(
            "reset_password.html",
            {
                "request": request,
                "lang": lang,
                "t": t,
                "email": email,
                "error": t.get("error_code_invalid", "Invalid code")
            }
        )

    # 3. Verify OTP
    if not verify_otp(db, user.id, code):
        return templates.TemplateResponse(
            "reset_password.html",
            {
                "request": request,
                "lang": lang,
                "t": t,
                "email": email,
                "error": t.get("error_code_invalid", "Invalid code")
            }
        )

    # 4. Update Password
    user.hashed_password = hash_password(new_password)
    user.failed_login_attempts = 0
    user.locked_until = None

    db.commit()

    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "lang": lang,
            "t": t,
            "success": t.get("success_reset", "Password changed!")
        }
    )

# =====================================================
# REGISTER PAGE (GET)
# =====================================================
@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    lang = request.query_params.get("lang", "pt")

    if lang not in ("pt", "en", "es", "fr", "de"):
        lang = "pt"

    t = get_texts(lang)

    return templates.TemplateResponse(
        "register.html",
        {
            "request": request,
            "lang": lang,
            "t": t
        }
    )

# =====================================================
# REGISTER (POST)
# =====================================================
@router.post("/register", response_class=HTMLResponse)
@limiter.limit("5/minute")
def register(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    phone: str = Form(None),
    two_factor_pref: str = Form("email"), # 'email' or 'telegram'
    lang: str = Form("pt"),
    db: Session = Depends(get_db)
):
    t = get_texts(lang)

    if get_user_by_email(db, email):
        return templates.TemplateResponse(
            "register.html",
            {
                "request": request,
                "lang": lang,
                "t": t,
                "error": t["error_email_exists"]
            }
        )

    # Validate Telegram Requirement
    if two_factor_pref == "telegram" and not phone:
        return templates.TemplateResponse(
            "register.html",
            {
                "request": request,
                "lang": lang,
                "t": t,
                "error": "Telegram Chat ID is required for Telegram authentication."
            }
        )

    # Password Matching Validation
    if password != confirm_password:
        return templates.TemplateResponse(
            "register.html",
            {
                "request": request,
                "lang": lang,
                "t": t,
                "error": "As senhas não coincidem." # Localization ideally handled via t[]
            }
        )

    # Complexity Validation (Backup for frontend)
    # At least 8 chars, 1 number, 1 special char
    import re
    if len(password) < 8 or not re.search(r"\d", password) or not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return templates.TemplateResponse(
            "register.html",
            {
                "request": request,
                "lang": lang,
                "t": t,
                "error": "Senha fraca. Use no mínimo 8 caracteres, números e símbolos."
            }
        )

    hashed_password = hash_password(password)

    # ✅ Captura o usuário criado
    user = create_user(
        db=db,
        name=name,
        email=email,
        hashed_password=hashed_password
    )

    # Configure 2FA & Phone
    if phone:
        user.phone_number = phone

    user.two_factor_enabled = True # Mandatory
    user.two_factor_method = two_factor_pref
    db.commit()

    # =================================================
    # 📧 VERIFICAÇÃO DE E-MAIL (PREPARAÇÃO PROFISSIONAL)
    # =================================================
    verification = create_email_verification(db, user.id)

    # Enqueue Verification Email
    enqueue_email(db, user.id, "verification_code", {"code": verification.code})

    # Enqueue Welcome Email
    enqueue_email(db, user.id, "welcome", {})

    # Enqueue Telegram Welcome (if applicable)
    enqueue_telegram(db, user.id, "telegram_welcome", {})

    return RedirectResponse(
        url=f"/verify-email?user_id={user.id}&lang={lang}",
        status_code=302
    )


