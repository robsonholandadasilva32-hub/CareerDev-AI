from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models.user import User

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/security", response_class=HTMLResponse)
def security_panel(request: Request, db: Session = Depends(get_db)):
    user = db.query(User).first()

    # 🛡️ PROTEÇÃO ABSOLUTA: nunca acessar atributos se user for None
    if user is None:
        return templates.TemplateResponse(
            "security.html",
            {
                "request": request,
                "two_factor_enabled": False,
                "two_factor_method": None,
                "no_user": True
            }
        )

    return templates.TemplateResponse(
        "security.html",
        {
            "request": request,
            "two_factor_enabled": bool(user.two_factor_enabled),
            "two_factor_method": user.two_factor_method,
            "no_user": False
        }
    )

@router.post("/security/update")
def update_security(
    two_factor: str = Form(None),
    method: str = Form(None),
    db: Session = Depends(get_db)
):
    user = db.query(User).first()

    # Se não houver usuário, não faz nada (defensivo)
    if user is None:
        return RedirectResponse("/security", status_code=302)

    if two_factor == "on":
        user.two_factor_enabled = 1
        user.two_factor_method = method
    else:
        user.two_factor_enabled = 0
        user.two_factor_method = None

    db.commit()
    return RedirectResponse("/security", status_code=302)

