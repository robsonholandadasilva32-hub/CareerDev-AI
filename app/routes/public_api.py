from fastapi import APIRouter, Depends, Response, Request
from fastapi.responses import Response, JSONResponse
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models.user import User
from app.db.models.career import CareerProfile
from app.core.auth_guard import get_current_user_from_request
from app.services.pdf_generator import generate_career_passport_pdf

router = APIRouter()

@router.get("/api/export/passport")
async def export_passport(
    request: Request,
    db: Session = Depends(get_db)
):
    user_id = get_current_user_from_request(request)
    if not user_id:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    current_user = request.state.user # AuthMiddleware populates this
    profile = db.query(CareerProfile).filter(CareerProfile.user_id == user_id).first()

    # Mock data if profile incomplete
    reality_data = profile.skills_snapshot if profile and profile.skills_snapshot else {"Python": 100}
    alignment_score = profile.market_relevance_score if profile and profile.market_relevance_score else 0
    # Mock action plan
    action_plan = [{"title": "Complete Profile", "status": "Todo"}]

    pdf_bytes = generate_career_passport_pdf(
        user_name=current_user.name,
        reality_data=reality_data,
        alignment_score=alignment_score,
        action_plan=action_plan
    )

    return Response(content=pdf_bytes, media_type="application/pdf", headers={
        "Content-Disposition": f"attachment; filename={current_user.name}_Passport.pdf"
    })

@router.get("/api/badge/{user_id}")
async def get_badge(user_id: int, db: Session = Depends(get_db)):
    profile = db.query(CareerProfile).filter(CareerProfile.user_id == user_id).first()
    score = profile.market_relevance_score if profile and profile.market_relevance_score else 0

    # Color logic
    if score < 50:
        color = "#ef4444" # Red
    elif score < 80:
        color = "#eab308" # Yellow
    else:
        color = "#22c55e" # Green

    svg = f"""
    <svg width="200" height="40" xmlns="http://www.w3.org/2000/svg">
      <linearGradient id="b" x2="0" y2="100%">
        <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
        <stop offset="1" stop-opacity=".1"/>
      </linearGradient>
      <mask id="a">
        <rect width="200" height="40" rx="3" fill="#fff"/>
      </mask>
      <g mask="url(#a)">
        <path fill="#202225" d="M0 0h110v40H0z"/>
        <path fill="{color}" d="M110 0h90v40H110z"/>
        <path fill="url(#b)" d="M0 0h200v40H0z"/>
      </g>
      <g fill="#fff" text-anchor="middle" font-family="DejaVu Sans,Verdana,Geneva,sans-serif" font-size="14">
        <text x="55" y="25" fill="#010101" fill-opacity=".3">CareerDev Score</text>
        <text x="55" y="24">CareerDev Score</text>
        <text x="155" y="25" fill="#010101" fill-opacity=".3">{score}/100</text>
        <text x="155" y="24">{score}/100</text>
      </g>
    </svg>
    """

    return Response(content=svg, media_type="image/svg+xml")
