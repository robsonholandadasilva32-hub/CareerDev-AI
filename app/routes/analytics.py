from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.career_engine import career_engine
from app.core.dependencies import get_user_with_profile

router = APIRouter()

@router.get("/api/analytics/skill-timeline")
async def skill_timeline(
    user=Depends(get_user_with_profile),
    db: Session = Depends(get_db)
):
    return await career_engine.get_skill_timeline(db, user)
