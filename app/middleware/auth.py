from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from app.core.jwt import decode_token
from app.db.session import SessionLocal
from app.db.models.user import User
from app.db.models.security import UserSession
import logging
from datetime import datetime, timedelta

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
                    sid = payload.get("sid")

                    db = SessionLocal()
                    try:
                        # Session Verification (if sid exists)
                        valid_session = True
                        if sid:
                            session = db.query(UserSession).filter(UserSession.id == sid).first()
                            if not session or not session.is_active:
                                logger.warning(f"AuthMiddleware: Revoked/Invalid Session {sid} for user {user_id}")
                                valid_session = False
                            else:
                                # Optimization: Only update last_active if > 1 minute has passed
                                if session.last_active_at < datetime.utcnow() - timedelta(minutes=1):
                                    session.last_active_at = datetime.utcnow()
                                    db.commit()

                        if valid_session:
                            user = db.query(User).filter(User.id == user_id).first()
                            if user:
                                request.state.user = user
                    finally:
                        db.close()
            except Exception as e:
                logger.debug(f"Auth Middleware Error: {e}")
                pass

        response = await call_next(request)
        return response
