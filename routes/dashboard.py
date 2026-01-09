from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.core.jwt import decode_token

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    # 1️⃣ Recupera o token JWT do cookie
    token = request.cookies.get("access_token")

    if not token:
        return RedirectResponse("/login")

    # 2️⃣ Decodifica e valida o token
    payload = decode_token(token)

    if not payload:
        return RedirectResponse("/login")

    # 3️⃣ Renderiza o dashboard com dados seguros do token
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user_id": payload.get("sub"),
            "email": payload.get("email")
        }
    )

