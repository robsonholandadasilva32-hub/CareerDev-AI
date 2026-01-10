from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.core.jwt import decode_token
from app.services.career_engine import career_engine
from app.i18n.loader import get_texts
from app.db.session import get_db
from app.db.models.user import User
from app.middleware.subscription import check_subscription_status

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

    user_id = int(payload.get("sub"))

    # 2.5️⃣ Check Subscription Status
    # We need to fetch the user object to check created_at and subscription fields
    # Since we don't have dependency injection for DB here easily without refactoring the whole route signature,
    # we will do a quick session.
    from app.db.session import SessionLocal
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            is_allowed = check_subscription_status(user)
            if not is_allowed:
                 # Redirect to Billing if trial expired
                 return RedirectResponse("/billing", status_code=302)
    finally:
        db.close()

    # 3️⃣ Career Data
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

