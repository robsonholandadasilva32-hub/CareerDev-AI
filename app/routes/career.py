import asyncio
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.auth_guard import get_current_user_from_request
from app.services.resume import process_resume_upload_async
from app.services.onboarding import validate_onboarding_access
from app.db.models.user import User
import logging
import openai
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.post("/analyze-resume", response_class=JSONResponse)
async def analyze_resume(
    request: Request,
    resume_text: str = Form(...),
    db: Session = Depends(get_db)
):
    user_id = get_current_user_from_request(request)
    if not user_id:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    # GUARD: Ensure Onboarding is Complete
    user = request.state.user
    redirect = validate_onboarding_access(user)
    if redirect:
        return redirect

    try:
        result = await process_resume_upload_async(db, user_id, resume_text)
        return JSONResponse(result)
    except Exception as e:
        logger.error(f"Error analyzing resume: {e}")
        return JSONResponse({"error": "Failed to analyze"}, status_code=500)

@router.get("/analytics", response_class=HTMLResponse)
async def analytics_dashboard(request: Request, db: Session = Depends(get_db)):
    # 1. Auth & Onboarding Guard
    user_id = get_current_user_from_request(request)
    if not user_id:
        return RedirectResponse("/login")

    user = request.state.user

    # GUARD: Ensure Onboarding is Complete
    redirect = validate_onboarding_access(user)
    if redirect:
        return redirect

    # 3. Data Preparation (Mock Data for MVP)
    analytics_data = {
        "dates": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
        "skills_growth": [10, 25, 40, 55, 70, 85],
        "market_demand": [80, 85, 80, 90, 95, 95],
        "radar_labels": ["Python", "System Design", "Cloud", "Soft Skills", "Algorithms"],
        "radar_data_user": [70, 60, 40, 80, 65],
        "radar_data_market": [90, 80, 90, 70, 80]
    }

    return templates.TemplateResponse("career/analytics.html", {
        "request": request,
        "user": user,
        "data": analytics_data,
    })

@router.post("/generate-linkedin-post", response_class=JSONResponse)
async def generate_linkedin_post(
    request: Request,
    db: Session = Depends(get_db)
):
    user_id = get_current_user_from_request(request)
    if not user_id:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    # Re-query user to avoid DetachedInstanceError from AuthMiddleware
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return JSONResponse({"error": "User not found"}, status_code=404)

    profile = user.career_profile

    # Determine Top Skill
    skill = "Software Engineering"
    if profile and profile.skills_snapshot:
        skills = profile.skills_snapshot
        if skills:
            # Sort by value descending
            skill = max(skills, key=skills.get)

    prompt = f"Write a short, professional, yet humble LinkedIn post announcing that I just received my Career Strategy Report. Mention my top skill ({skill}) and include a hashtag #CareerDevAI."

    if not settings.OPENAI_API_KEY:
        # Mock Response
        return JSONResponse({
            "post": f"Excited to share that I just received my Career Strategy Report from CareerDev AI! 🚀\n\nIt confirmed that my focus on {skill} is paying off. Looking forward to the next steps in my journey.\n\n#CareerDevAI #CareerGrowth #{skill.replace(' ', '')}"
        })

    try:
        openai.api_key = settings.OPENAI_API_KEY
        response = await asyncio.to_thread(
            openai.chat.completions.create,
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a professional career coach helper."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        content = response.choices[0].message.content
        return JSONResponse({"post": content.strip().strip('"')})
    except Exception as e:
        logger.error(f"Error generating LinkedIn post: {e}")
        return JSONResponse({"error": "Failed to generate post"}, status_code=500)
