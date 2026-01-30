from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from app.core.jwt import decode_token
from app.db.session import SessionLocal
from app.db.models.user import User
from app.db.models.security import UserSession
import logging
from datetime import datetime, timedelta
import asyncio

logger = logging.getLogger(__name__)
templates = Jinja2Templates(directory="app/templates")

def _process_auth_sync(user_id: int, sid: str):
    """
    Synchronously handle database operations for authentication.
    Returns a tuple: (user_object, is_banned_flag)
    """
    db = SessionLocal()
    user = None
    is_banned = False
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
                # Eagerly load fields if necessary, or rely on them being present.
                # Since session closes, we rely on the object being detached but data present.
                # We check is_banned immediately.
                if user.is_banned:
                    is_banned = True
                    # We don't return the user if banned, effectively
    except Exception as e:
        logger.error(f"Error in _process_auth_sync: {e}")
        # In case of DB error, we treat as not authenticated
        pass
    finally:
        db.close()

    return user, is_banned

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
                    user, is_banned = await asyncio.to_thread(_process_auth_sync, user_id, sid)

                    if user:
                        if is_banned:
                            logger.warning(f"AuthMiddleware: Banned user {user_id} attempted access.")
                            if "application/json" in request.headers.get("accept", "") or request.url.path.startswith("/api"):
                                    return JSONResponse(status_code=403, content={"detail": "Access Revoked"})
                            return templates.TemplateResponse("errors/403_banned.html", {"request": request}, status_code=403)

                        request.state.user = user

            except Exception as e:
                logger.debug(f"Auth Middleware Error: {e}")
                # Pass through to allow call_next to handle unauthenticated state (or handle it in endpoints)
                pass

        # Fall through: Always ensure we return the result of call_next if no early return occurred
        response = await call_next(request)
        return response
