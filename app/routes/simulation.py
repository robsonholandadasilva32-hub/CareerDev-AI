from fastapi import APIRouter, Depends
from app.core.dependencies import get_user_with_profile
from app.services.career_engine import career_engine

router = APIRouter()

@router.post("/api/simulate-skill-path")
async def simulate_skill_path(payload: dict, user=Depends(get_user_with_profile)):
    skill = payload.get("skill")
    months = payload.get("months", 6)

    return career_engine.simulate_skill_path(user, skill, months)
