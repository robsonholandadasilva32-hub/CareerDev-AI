from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime
import user_agents

from app.db.session import SessionLocal
from app.db.models.user import User
from app.db.models.security import UserSession
from app.db.models.audit import AuditLog
from app.core.jwt import decode_token
from app.services.onboarding import validate_onboarding_access
from app.services.security_service import get_active_sessions, get_all_user_sessions, revoke_session, log_audit
from app.core.config import settings
from app.core.utils import get_client_ip
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(request: Request, db: Session) -> User | None:
    # Use the user object already validated by AuthMiddleware
    # This ensures we respect session revocation/banning checks done there.
    return getattr(request.state, "user", None)

def parse_agent(ua_string: str) -> str:
    """Parses user agent string into a readable format."""
    try:
        user_agent = user_agents.parse(ua_string)
        return str(user_agent) # Returns "PC / Windows / Chrome" format usually
    except Exception:
        return "Unknown Device"

@router.get("/dashboard/security", response_class=HTMLResponse)
def security_panel(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)

    # 🛡️ PROTEÇÃO ABSOLUTA: nunca acessar atributos se user for None
    if user is None:
        return RedirectResponse("/login", status_code=302)

    # GUARD: Ensure Onboarding is Complete
    if resp := validate_onboarding_access(user):
        return resp

    # Get SID for highlighting current session
    token = request.cookies.get("access_token")
    payload = decode_token(token) if token else {}
    current_sid = payload.get("sid")

    # Current Session Data
    current_ua_string = request.headers.get("user-agent", "")
    current_device = parse_agent(current_ua_string)
    current_ip = get_client_ip(request)

    # Fetch Real Sessions (History from Audit Log)
    history = db.query(AuditLog).filter(AuditLog.user_id == user.id).order_by(desc(AuditLog.login_timestamp)).limit(20).all()

    # Process Sessions for Display
    processed_sessions = []
    for h in history:
        is_current = (str(h.session_id) == str(current_sid))
        status = "Expired"
        if h.is_active_session:
             status = "Current" if is_current else "Active"

        processed_sessions.append({
            "id": h.session_id, # Use session_id for revocation
            "device": f"{h.device_type} ({h.browser})",
            "ip_address": h.ip_address,
            "last_active": h.login_timestamp, # Using Login Timestamp
            "is_current": is_current,
            "status": status,
            "raw_ua": h.user_agent_raw,
            "os": h.os
        })

    return templates.TemplateResponse(
        "dashboard/security.html",
        {
            "request": request,
            "no_user": False,
            "user": user,
            "current_device": current_device,
            "current_ip": current_ip,
            "sessions": processed_sessions,
            "current_sid": current_sid
        }
    )

@router.post("/dashboard/security/update")
def update_security(
    request: Request,
    db: Session = Depends(get_db)
):
    # This route previously updated language.
    # Now it does nothing or could update other preferences.
    # For now, we just redirect back.

    user = get_current_user(request, db)
    if not user:
         return RedirectResponse("/login", status_code=302)

    # GUARD: Ensure Onboarding is Complete
    if resp := validate_onboarding_access(user):
        return resp

    return RedirectResponse("/dashboard/security?success=true", status_code=302)

@router.post("/dashboard/security/delete-account")
def delete_account(
    request: Request,
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)

    # No notifications sent.

    # Delete User (Cascade deletes profile/plans due to relationship config)
    db.delete(user)
    db.commit()

    # Logout
    response = RedirectResponse("/login?msg=account_deleted", status_code=302)
    response.delete_cookie("access_token")
    return response

@router.get("/api/security/sessions")
def get_login_history(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized"})

    # Get current session ID
    token = request.cookies.get("access_token")
    payload = decode_token(token) if token else {}
    current_sid = payload.get("sid")

    history = db.query(AuditLog).filter(AuditLog.user_id == user.id).order_by(desc(AuditLog.login_timestamp)).limit(20).all()

    response_data = []
    for h in history:
        status = "Expired"
        if h.is_active_session:
            status = "Current" if str(h.session_id) == str(current_sid) else "Active"

        response_data.append({
            "device": f"{h.device_type} ({h.browser})",
            "ip": h.ip_address,
            "location": "Unknown",
            "date": h.login_timestamp.strftime("%Y-%m-%d %H:%M"),
            "status": status,
            "os": h.os
        })

    return JSONResponse(content=response_data)

@router.post("/dashboard/security/revoke_all")
def revoke_all_sessions(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)

    # Get current session ID
    token = request.cookies.get("access_token")
    payload = decode_token(token) if token else {}
    current_sid = payload.get("sid")

    if not current_sid:
        return RedirectResponse("/login", status_code=302)

    # Revoke all UserSessions except current
    db.query(UserSession).filter(
        UserSession.user_id == user.id,
        UserSession.id != current_sid
    ).update({UserSession.is_active: False}, synchronize_session=False)

    # Revoke all AuditLog except current
    db.query(AuditLog).filter(
        AuditLog.user_id == user.id,
        AuditLog.session_id != current_sid
    ).update({AuditLog.is_active_session: False}, synchronize_session=False)

    db.commit()
    log_audit(db, user.id, "REVOKE_ALL_SESSIONS", get_client_ip(request), "Revoked all other sessions")

    return RedirectResponse("/dashboard/security", status_code=303)

@router.post("/dashboard/security/revoke/{session_id}")
def revoke_user_session_route(session_id: str, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)

    # Security: Ensure session belongs to user
    session_to_revoke = db.query(UserSession).filter(UserSession.id == session_id, UserSession.user_id == user.id).first()
    if session_to_revoke:
        revoke_session(db, session_id)
        # Also revoke AuditLog
        db.query(AuditLog).filter(AuditLog.session_id == session_id).update({AuditLog.is_active_session: False})
        db.commit()
        log_audit(db, user.id, "REVOKE_SESSION", get_client_ip(request), f"Revoked session {session_id}")

    return RedirectResponse("/dashboard/security", status_code=303)
