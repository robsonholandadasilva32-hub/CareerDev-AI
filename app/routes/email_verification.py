from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.crud.email_verification import get_verification_by_user, verify_code
from app.i18n.loader import get_texts

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# =====================================================
# VERIFY EMAIL PAGE (GET)
# =====================================================
@router.get("/verify-email", response_class=HTMLResponse)
def verify_email_page(
    request: Request,
    user_id: int,
    lang: str = "pt"
):
    t = get_texts(lang)

    return templates.TemplateResponse(
        "verify_email.html",
        {
            "request": request,
            "user_id": user_id,
            "lang": lang,
            "t": t
        }
    )

# =====================================================
# VERIFY EMAIL (POST)
# =====================================================
@router.post("/verify-email", response_class=HTMLResponse)
def verify_email(
    request: Request,
    user_id: int = Form(...),
    code: str = Form(...),
    lang: str = Form("pt"),
    db: Session = Depends(get_db)
):
    t = get_texts(lang)

    if not verify_code(db, user_id, code):
        return templates.TemplateResponse(
            "verify_email.html",
            {
                "request": request,
                "user_id": user_id,
                "lang": lang,
                "t": t,
                "error": t.get("error_invalid_code", "Código inválido")
            }
        )

    return RedirectResponse(
        url=f"/login?lang={lang}",
        status_code=302
    )

