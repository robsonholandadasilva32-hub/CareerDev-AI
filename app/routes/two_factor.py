from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.jwt import decode_token, create_access_token
from app.services.notifications import verify_otp
from app.i18n.loader import get_texts

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/verify-2fa", response_class=HTMLResponse)
def verify_2fa_page(request: Request):
    lang = request.query_params.get("lang", "pt")
    t = get_texts(lang)

    return templates.TemplateResponse(
        "verify_2fa.html",
        {
            "request": request,
            "lang": lang,
            "t": t
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
        })

        response = RedirectResponse("/dashboard", status_code=302)
        response.delete_cookie("temp_token")
        response.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            secure=False,
            samesite="lax"
        )
        return response

    return templates.TemplateResponse(
        "verify_2fa.html",
        {
            "request": request,
            "lang": lang,
            "t": t,
            "error": t.get("error_invalid_code", "Invalid code")
        }
    )
