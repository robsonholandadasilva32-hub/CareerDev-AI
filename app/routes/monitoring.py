from fastapi import APIRouter, HTTPException, Request, Depends, status
from pydantic import BaseModel
import sentry_sdk
from app.core.config import settings
from openai import AsyncOpenAI
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

class PostureAnalysisRequest(BaseModel):
    image: str # Base64 encoded image or Data URL

# Initialize OpenAI client
client = None
if settings.OPENAI_API_KEY:
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
else:
    logger.warning("OPENAI_API_KEY not found. Monitoring service will fail.")

async def check_auth(request: Request):
    if not getattr(request.state, "user", None):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return request.state.user

@router.post("/analyze-posture")
async def analyze_posture(data: PostureAnalysisRequest, user = Depends(check_auth)):
    if not client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service unavailable"
        )

    # Ensure correct format for OpenAI
    image_url = data.image
    if not image_url.startswith("data:"):
        # Assume JPEG if no header, but safest to require Data URL from frontend
        image_url = f"data:image/jpeg;base64,{data.image}"

    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Analyze this image. Is the user slouching or exhibiting poor ergonomic posture? Answer strictly 'YES' or 'NO'."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_url
                            },
                        },
                    ],
                }
            ],
            max_tokens=10
        )
        result = response.choices[0].message.content.strip().upper()

        # Clean up any extra punctuation (e.g., "YES.")
        if "YES" in result:
            result = "YES"
        elif "NO" in result:
            result = "NO"

    except Exception as e:
        logger.error(f"OpenAI Vision Error: {e}")
        sentry_sdk.capture_exception(e)
        raise HTTPException(status_code=500, detail="Failed to analyze image")

    if result == "YES":
        # Bad posture
        sentry_sdk.capture_message(f"Poor Posture Detected for User {user.id}", level="warning")
        return {"status": "poor_posture", "message": "Posture Check: Time to straighten up!"}

    return {"status": "good_posture", "message": "Great posture! Keep it up."}
