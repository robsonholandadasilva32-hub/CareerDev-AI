from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.i18n.loader import get_texts
from app.core.security import verify_password, hash_password
from app.core.jwt import create_access_token
from app.db.crud.users import get_user_by_email, create_user
from app.db.crud.email_verification import create_email_verification
from app.db.session import get_db

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# =====================================================
# LOGIN PAGE (GET)
# =====================================================
@router.get("/", response_class=HTMLResponse)
@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    lang = request.query_params.get("lang")

    if lang not in ("pt", "en", "es"):
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
def login(
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

    if not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "lang": lang,
                "t": t,
                "error": t["error_invalid_password"]
            }
        )

    # 🔐 JWT (FASE 2 – correto e funcional)
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
        secure=False,  # HTTPS = True em produção
        samesite="lax"
    )

    return response

# =====================================================
# REGISTER PAGE (GET)
# =====================================================
@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    lang = request.query_params.get("lang", "pt")

    if lang not in ("pt", "en", "es"):
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
def register(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
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

    hashed_password = hash_password(password)

    # ✅ Captura o usuário criado
    user = create_user(
        db=db,
        name=name,
        email=email,
        hashed_password=hashed_password
    )

    # =================================================
    # 📧 VERIFICAÇÃO DE E-MAIL (PREPARAÇÃO PROFISSIONAL)
    # =================================================
    verification = create_email_verification(db, user.id)

    # ⚠️ Em dev: apenas loga o código
    print(f"[DEV] Código de verificação de e-mail: {verification.code}")

    return RedirectResponse(
        url=f"/verify-email?user_id={user.id}&lang={lang}",
        status_code=302
    )


