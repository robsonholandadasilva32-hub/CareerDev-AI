from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.core.jwt import decode_token
from app.services.career_engine import career_engine
from app.i18n.loader import get_texts

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

    # 3️⃣ Career Data
    user_id = int(payload.get("sub"))
    profile = career_engine.analyze_profile(user_id)
    plan = career_engine.generate_plan(user_id)

    # 4️⃣ Load Language
    lang = request.query_params.get("lang")
    if not lang:
        lang = request.session.get("lang", "pt")

    t = get_texts(lang)

    # 5️⃣ Renderiza o dashboard com dados seguros do token
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user_id": user_id,
            "email": payload.get("email"),
            "profile": profile,
            "plan": plan,
            "t": t,
            "lang": lang
        }
    )

