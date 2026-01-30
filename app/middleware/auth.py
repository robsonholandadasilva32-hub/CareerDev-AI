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
from typing import Optional

logger = logging.getLogger(__name__)
templates = Jinja2Templates(directory="app/templates")

class AuthMiddleware(BaseHTTPMiddleware):

    def _authenticate_user_sync(self, user_id: int, sid: Optional[str]) -> Optional[User]:
        """
        Synchronous helper to handle DB operations for user authentication.
        To be run in a threadpool.
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
                    # Pre-load is_banned if needed (it's a column, so it's there)
                    # Returning the user object. Note: it will be detached when db closes.
                    # Ensure we don't access lazy relationships later without a session.
                    db.expunge(user) # Explicitly detach so we know what we are dealing with
                    return user
            return None
        except Exception as e:
            logger.debug(f"Auth Logic Error: {e}")
            return None
        finally:
            db.close()

    async def dispatch(self, request: Request, call_next):
        request.state.user = None

        token = request.cookies.get("access_token")
        if token:
            try:
                payload = decode_token(token)
                if payload:
                    user_id = int(payload.get("sub"))
                    sid = payload.get("sid")

                    # Offload Sync DB Ops to Thread using Starlette's native helper
                    user = await run_in_threadpool(self._authenticate_user_sync, user_id, sid)

                    if user:
                        if user.is_banned:
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