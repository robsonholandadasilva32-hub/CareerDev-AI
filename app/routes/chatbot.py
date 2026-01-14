from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.ai.chatbot import chatbot_service
from app.db.session import get_db
from app.core.jwt import decode_token

router = APIRouter(prefix="/chatbot")

class ChatMessage(BaseModel):
    message: str

@router.post("/message")
def chat(
    request: Request,
    message: ChatMessage,
    db: Session = Depends(get_db)
):
    # Try to get user context from token
    user_id = None
    token = request.cookies.get("access_token")
    if token:
        payload = decode_token(token)
        if payload:
            user_id = int(payload.get("sub"))

    # Determine language (simple check or session)
    lang = request.session.get("lang", "pt")

    response = chatbot_service.get_response(
        message=message.message,
        lang=lang,
        user_id=user_id,
        db=db
    )
    return {"response": response}
