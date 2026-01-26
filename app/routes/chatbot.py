from fastapi import APIRouter, Request, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.ai.chatbot import chatbot_service
from app.core.auth_guard import get_current_user_from_request
from app.core.limiter import limiter

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    mode: str = "standard"
    lang: str = "en"

@router.post("/message")
@limiter.limit("10/minute")
async def chat_endpoint(request: Request, chat_req: ChatRequest, db: Session = Depends(get_db)):
    user_id = get_current_user_from_request(request)

    response = await chatbot_service.get_response(
        chat_req.message,
        chat_req.lang,
        user_id=user_id,
        db=db,
        mode=chat_req.mode
    )

    return {"response": response}
