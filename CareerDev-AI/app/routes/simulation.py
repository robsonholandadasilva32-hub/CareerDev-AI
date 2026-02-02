from fastapi import APIRouter, Depends
from app.routes.dashboard import get_current_user_secure
from app.services.career_engine import career_engine

router = APIRouter()

@router.post("/api/simulate-skill-path")
async def simulate_skill_path(payload: dict, user=Depends(get_current_user_secure)):
    skill = payload.get("skill")
    months = payload.get("months", 6)

    return career_engine.simulate_skill_path(user, skill, months)
