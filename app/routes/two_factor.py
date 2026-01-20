from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.jwt import decode_token, create_access_token
from app.services.notifications import verify_otp, create_otp
from app.i18n.loader import get_texts
from app.db.models.user import User

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.post("/resend-2fa")
def resend_2fa(
    request: Request,
    db: Session = Depends(get_db)
):
    temp_token = request.cookies.get("temp_token")
    if not temp_token:
        return RedirectResponse("/login", status_code=302)

    payload = decode_token(temp_token)
    if not payload or not payload.get("pre_2fa"):
        return RedirectResponse("/login", status_code=302)

    user_id = int(payload["sub"])
    user = db.query(User).filter(User.id == user_id).first()

    if user:
        method = user.two_factor_method or "email"
        create_otp(db, user_id, method)
        # In prod: Add flash message "Code resent"

    return RedirectResponse("/verify-2fa", status_code=302)

@router.get("/verify-2fa", response_class=HTMLResponse)
def verify_2fa_page(request: Request):
    lang = request.query_params.get("lang", "pt")
    t = get_texts(lang)

    return templates.TemplateResponse(
        "verify_2fa.html",
        {
            "request": request,
            "lang": lang,
            "t": t,
            "page_title": "Verificação de Segurança",
            "instructions": "Este é um passo extra para proteger sua conta. Digite abaixo o código temporário enviado para você.",
            "form_action": "/verify-2fa",
            "resend_action": "/resend-2fa"
        }
    )

@router.post("/verify-2fa", response_class=HTMLResponse)
def verify_2fa(
    request: Request,
    code: str = Form(...),
    db: Session = Depends(get_db)
):
    lang = request.query_params.get("lang", "pt")
    t = get_texts(lang)

    temp_token = request.cookies.get("temp_token")
    if not temp_token:
        return RedirectResponse("/login")

    payload = decode_token(temp_token)
    if not payload or not payload.get("pre_2fa"):
        return RedirectResponse("/login")

    user_id = int(payload["sub"])
    email = payload["email"]

    if verify_otp(db, user_id, code):
        # Issue real token
        token = create_access_token({
            "sub": str(user_id),
            "email": email,
            "2fa": True
        }, expires_minutes=30) # Short session validity

        response = RedirectResponse("/dashboard", status_code=302)
        response.delete_cookie("temp_token")
        response.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            secure=request.url.scheme == "https", # Auto-detect HTTPS
            samesite="lax"
        )
        return response

    return templates.TemplateResponse(
        "verify_2fa.html",
        {
            "request": request,
            "lang": lang,
            "t": t,
            "page_title": "Verificação de Segurança",
            "instructions": "Este é um passo extra para proteger sua conta. Digite abaixo o código temporário enviado para você.",
            "form_action": "/verify-2fa",
            "resend_action": "/resend-2fa",
            "error": t.get("error_invalid_code", "Invalid code")
        }
    )
