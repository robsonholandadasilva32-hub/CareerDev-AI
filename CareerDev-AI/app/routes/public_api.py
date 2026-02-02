from fastapi import APIRouter, Depends, Response, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from app.db.session import get_db
from app.db.models.user import User
from app.routes.dashboard import get_current_user_secure
from app.services.pdf_generator import generate_career_passport

router = APIRouter()

@router.get("/api/export/passport")
def export_passport(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_secure)
):
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    pdf_buffer = generate_career_passport(user, db)

    # Sanitize filename (remove quotes if any) and wrap in quotes
    safe_name = (user.name or 'User').replace('"', '').replace("'", "")
    headers = {
        "Content-Disposition": f'attachment; filename="{safe_name}_CareerPassport.pdf"'
    }

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers=headers
    )

@router.get("/api/badge/{user_id}")
def get_user_badge(user_id: int, db: Session = Depends(get_db)):
    # Public Endpoint - No Auth Required
    user = db.query(User).options(joinedload(User.career_profile)).filter(User.id == user_id).first()

    if not user:
        # Return a generic 404 badge or simple SVG error
        return Response(content=_generate_badge_svg(0, "User Not Found"), media_type="image/svg+xml")

    profile = user.career_profile
    score = profile.market_relevance_score if profile else 0

    svg_content = _generate_badge_svg(score)

    return Response(content=svg_content, media_type="image/svg+xml")

def _generate_badge_svg(score: int, label_override: str = None) -> str:
    # Color Logic
    color = "#ff0055" # Red
    if score >= 80:
        color = "#00ff88" # Green
    elif score >= 50:
        color = "#ff9900" # Yellow

    score_text = f"{score}/100" if not label_override else "N/A"

    # SVG Template (Shields.io style)
    # Width calculation is approximate
    width_left = 110
    width_right = 60
    total_width = width_left + width_right

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{total_width}" height="20">
    <linearGradient id="b" x2="0" y2="100%">
        <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
        <stop offset="1" stop-opacity=".1"/>
    </linearGradient>
    <mask id="a">
        <rect width="{total_width}" height="20" rx="3" fill="#fff"/>
    </mask>
    <g mask="url(#a)">
        <path fill="#555" d="M0 0h{width_left}v20H0z"/>
        <path fill="{color}" d="M{width_left} 0h{width_right}v20H{width_left}z"/>
        <path fill="url(#b)" d="M0 0h{total_width}v20H0z"/>
    </g>
    <g fill="#fff" text-anchor="middle" font-family="DejaVu Sans,Verdana,Geneva,sans-serif" font-size="11">
        <text x="{width_left/2}" y="15" fill="#010101" fill-opacity=".3">CareerDev Score</text>
        <text x="{width_left/2}" y="14">CareerDev Score</text>
        <text x="{width_left + width_right/2}" y="15" fill="#010101" fill-opacity=".3">{score_text}</text>
        <text x="{width_left + width_right/2}" y="14">{score_text}</text>
    </g>
</svg>"""
    return svg
