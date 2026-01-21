from datetime import datetime, timedelta
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.i18n.loader import get_texts
from app.core.security import verify_password, hash_password
from app.core.jwt import create_access_token
from app.db.crud.users import get_user_by_email, create_user
from app.db.session import get_db
from app.core.limiter import limiter
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

MAX_LOGIN_ATTEMPTS = 5
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
        
    # DIRECT REDIRECT TO DASHBOARD
    token = create_access_token({
        "sub": str(user.id),
        "email": user.email,
        "2fa": False # 2FA is no longer a concept, so False or True doesn't matter, but keeping structure clean
    })

    response = RedirectResponse("/dashboard", status_code=302)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="lax"
    )
    return response

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

    # Password Matching Validation
    if password != confirm_password:
        return templates.TemplateResponse(
            "register.html",
            {
                "request": request,
                "lang": lang,
                "t": t,
                "error": "As senhas não coincidem."
            }
        )

    # Complexity Validation
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

    # Create User - Email Verified by default
    user = create_user(
        db=db,
        name=name,
        email=email,
        hashed_password=hashed_password,
        email_verified=True
    )

    # Direct Login
    token = create_access_token({
        "sub": str(user.id),
        "email": user.email,
        "2fa": False
    })

    response = RedirectResponse("/dashboard", status_code=302)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="lax"
    )
    return response
