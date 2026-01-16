from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.auth_guard import get_current_user_from_request
from app.services.resume import process_resume_upload
from app.db.models.user import User
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.post("/analyze-resume", response_class=JSONResponse)
def analyze_resume(
    request: Request,
    resume_text: str = Form(...),
    db: Session = Depends(get_db)
):
    user_id = get_current_user_from_request(request)
    if not user_id:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    try:
        result = process_resume_upload(db, user_id, resume_text)
        return JSONResponse(result)
    except Exception as e:
        logger.error(f"Error analyzing resume: {e}")
        return JSONResponse({"error": "Failed to analyze"}, status_code=500)
