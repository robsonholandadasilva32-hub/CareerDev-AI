from fastapi import APIRouter, Depends
from app.services.career_engine import career_engine
from app.routes.dashboard import get_current_user_secure

router = APIRouter()

@router.post("/api/simulate")
async def simulate(payload: dict, user=Depends(get_current_user_secure)):
    skill = payload.get("skill")
    return career_engine.simulate_skill_path(user, skill)
