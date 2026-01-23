from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from app.core.jwt import decode_token
from app.db.session import SessionLocal
from app.db.models.user import User
import logging

logger = logging.getLogger(__name__)

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.user = None

        token = request.cookies.get("access_token")
        if token:
            try:
                payload = decode_token(token)
                if payload:
                    user_id = int(payload.get("sub"))
                    # We need a new session here because we are outside the dependency chain
                    db = SessionLocal()
                    try:
                        user = db.query(User).filter(User.id == user_id).first()
                        if user:
                            logger.info(f"DEBUG: Checking Token: {token} | User Completed? {user.is_profile_completed}")
                            request.state.user = user
                    finally:
                        db.close()
            except Exception as e:
                # Token might be invalid or DB error.
                # We log debug to avoid spamming logs on expired tokens
                logger.debug(f"Auth Middleware Error: {e}")
                pass

        response = await call_next(request)
        return response
