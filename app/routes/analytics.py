from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.career_engine import career_engine
from app.routes.dashboard import get_current_user_secure

router = APIRouter()

@router.get("/api/analytics/skill-timeline")
async def skill_timeline(
    user=Depends(get_current_user_secure),
    db: Session = Depends(get_db)
):
    return await career_engine.get_skill_timeline(db, user)
