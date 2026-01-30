from starlette.middleware.base import BaseHTTPMiddleware
from starlette.concurrency import run_in_threadpool
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from app.core.jwt import decode_token
from app.db.session import SessionLocal
from app.db.models.user import User
from app.db.models.security import UserSession
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
templates = Jinja2Templates(directory="app/templates")

class AuthBlockedError(Exception):
    """Raised when a banned user attempts to access the system."""
    def __init__(self, message: str, user_id: int):
        self.message = message
        self.user_id = user_id
        super().__init__(message)

def _authenticate_user_sync(user_id: int, sid: str):
    """
    Synchronous helper to handle database operations for user authentication.
    Executed in a threadpool to prevent blocking the async event loop.
    """
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
                if user.is_banned:
                    # Signal to the async caller that access is blocked
                    raise AuthBlockedError("Access Revoked", user_id)
                return user
        return None
    finally:
        db.close()

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

                    # Offload blocking DB operations to a thread
                    try:
                        user = await run_in_threadpool(_authenticate_user_sync, user_id, sid)
                        request.state.user = user
                    except AuthBlockedError as e:
                        logger.warning(f"AuthMiddleware: Banned user {e.user_id} attempted access.")
                        if "application/json" in request.headers.get("accept", "") or request.url.path.startswith("/api"):
                             return JSONResponse(status_code=403, content={"detail": e.message})
                        return templates.TemplateResponse("errors/403_banned.html", {"request": request}, status_code=403)

            except Exception as e:
                logger.debug(f"Auth Middleware Error: {e}")
                # Pass through to allow call_next to handle unauthenticated state (or handle it in endpoints)
                pass

        # Fall through: Always ensure we return the result of call_next if no early return occurred
        response = await call_next(request)
        return response
