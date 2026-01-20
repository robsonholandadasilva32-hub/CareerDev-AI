from fastapi import APIRouter
from app.core.config import settings
from app.services.notifications import send_raw_email
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/test-email")
async def test_email(to_email: str = settings.SMTP_FROM_EMAIL):
    try:
        logger.info(f"Debug: Sending test email to {to_email}")
        await send_raw_email(to_email, "Test Email from Debug Route", "This is a test email to verify SMTP connectivity.")
        return {"status": "success", "message": f"Email sent to {to_email}"}
    except Exception as e:
        logger.error(f"Debug: Failed to send test email: {e}")
        return {"status": "error", "message": str(e)}
