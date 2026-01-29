from fastapi import APIRouter, Depends
from app.routes.dashboard import get_current_user_secure
from app.services.career_engine import career_engine

router = APIRouter()

@router.get("/api/risk/explain")
async def explain_risk(user=Depends(get_current_user_secure)):
    return career_engine.explain_risk(user)
