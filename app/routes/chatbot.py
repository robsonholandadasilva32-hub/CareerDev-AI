from fastapi import APIRouter
from pydantic import BaseModel
from app.ai.chatbot import simple_ai_response

router = APIRouter(prefix="/chatbot")

class ChatMessage(BaseModel):
    message: str

@router.post("/message")
def chat(message: ChatMessage):
    response = simple_ai_response(message.message)
    return {"response": response}

