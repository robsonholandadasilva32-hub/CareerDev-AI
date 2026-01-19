from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.jwt import decode_token
from app.services.career_engine import career_engine
from app.i18n.loader import get_texts
from app.db.session import get_db
from app.db.models.user import User
from app.middleware.subscription import check_subscription_status

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def get_current_user_secure(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        return None

    payload = decode_token(token)
    if not payload:
        return None

    user_id = int(payload.get("sub"))
    user = db.query(User).filter(User.id == user_id).first()
    return user

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user_secure)):
    # 1️⃣ Secure Auth Dependency Check
    if not user:
        return RedirectResponse("/login", status_code=302)

    user_id = user.id
    email = user.email

    # 2.5️⃣ Check Subscription Status
    is_allowed = check_subscription_status(user)
    if not is_allowed:
            # Redirect to Billing if trial expired
            return RedirectResponse("/billing", status_code=302)

    # 3️⃣ Career Data (Real Logic)
    # This will create/update the profile and sync (simulated) external data
    profile_data = career_engine.analyze_profile(db, user_id)

    # Generate/Fetch Plan
    plan_items = career_engine.generate_plan(db, user_id)

    # 4️⃣ Load Language
    lang = request.query_params.get("lang")
    if not lang:
        lang = request.session.get("lang", "pt")

    t = get_texts(lang)

    # 5️⃣ Renderiza o dashboard
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user,
            "user_id": user_id,
            "email": email,
            "profile": profile_data,
            "plan": plan_items, # List of LearningPlan objects
            "badges": user.badges, # Pass UserBadges to template
            "t": t,
            "lang": lang
        }
    )
