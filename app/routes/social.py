from fastapi import APIRouter, Request, Depends, BackgroundTasks
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from authlib.integrations.starlette_client import OAuth
from sqlalchemy.orm import Session, joinedload
from app.core.config import settings
from app.db.session import get_db
from app.services.social_harvester import social_harvester
from app.db.crud.users import (
    get_user_by_email,
    get_user_by_github_id,
    get_user_by_linkedin_id,
    create_user_async
)
from app.db.models.user import User
from app.core.security import hash_password
from app.core.jwt import create_access_token
from app.services.onboarding import get_next_onboarding_step
from app.services.security_service import create_user_session, log_audit
from app.services.gamification import check_and_award_security_badge
from app.core.utils import get_client_ip
from app.core.limiter import limiter
import secrets
import logging
import os
import asyncio
import json
from datetime import datetime
from sqlalchemy.exc import IntegrityError
import user_agents
# CORREÇÃO: Importando o modelo com o nome correto
from app.db.models.audit import AuditLog

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
oauth = OAuth()

# GitHub Config
logger.info(f"GitHub Secret Loaded? {bool(settings.GITHUB_CLIENT_SECRET)}")
if settings.GITHUB_CLIENT_ID and settings.GITHUB_CLIENT_SECRET:
    oauth.register(
        name='github',
        client_id=settings.GITHUB_CLIENT_ID,
        client_secret=settings.GITHUB_CLIENT_SECRET,
        access_token_url='https://github.com/login/oauth/access_token',
        access_token_params=None,
        authorize_url='https://github.com/login/oauth/authorize',
        authorize_params=None,
        api_base_url='https://api.github.com/',
        client_kwargs={'scope': 'user:email'},
    )

# LinkedIn Config
raw_secret = os.environ.get('LINKEDIN_CLIENT_SECRET', '')
linkedin_secret = raw_secret.strip()

# Log length and first/last chars to detect hidden spaces or quotes
logger.error(f"DEBUG SOCIAL: Secret loaded? {bool(linkedin_secret)} | Stripped Length: {len(linkedin_secret)} | Value: {linkedin_secret[:2]}***{linkedin_secret[-1:] if linkedin_secret else ''}")

if settings.LINKEDIN_CLIENT_ID:
    if not linkedin_secret:
         raise ValueError("LINKEDIN_CLIENT_SECRET is present but empty!")

    oauth.register(
        name='linkedin',
        client_id=settings.LINKEDIN_CLIENT_ID,
        # Explicitly pass client_secret to avoid Authlib implicit loading issues
        client_secret=linkedin_secret,
        server_metadata_url='https://www.linkedin.com/oauth/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid profile email',
            'token_endpoint_auth_method': 'client_secret_post',
        }
    )

def get_current_user_onboarding(request: Request, db: Session = Depends(get_db)):
    # 🛡️ Relies on AuthMiddleware for session validation
    if not getattr(request.state, "user", None):
        return None
    # Re-query to attach to current db session
    return db.query(User).filter(User.id == request.state.user.id).first()

def login_user_and_redirect(request: Request, user, db: Session, redirect_url: str = "/dashboard"):
    # Update last_login
    user.last_login = datetime.utcnow()
    # Implicitly accept terms on login (Zero Touch)
    if not user.terms_accepted:
        user.terms_accepted = True
        user.terms_accepted_at = datetime.utcnow()

    # Zero Touch: If we have LinkedIn, we are good to go, but we want to check GitHub
    # Note: is_profile_completed is now largely semantic for "has github and terms"
    if user.linkedin_id and user.github_id and user.terms_accepted:
        user.is_profile_completed = True

    try:
        db.commit()
        logger.info(f"✅ DB COMMIT SUCCESS: User {user.id} logged in.")
    except Exception as e:
        logger.error(f"❌ DB COMMIT FAILED: {e}")
        raise e

    # Security: Create Session
    ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "unknown")
    logger.info(f"Creating session for user {user.id} | IP: {ip} | UA: {user_agent[:30]}...")
    sid = create_user_session(db, user.id, ip, user_agent)

    # Security: Persistent Audit Log (Forensic History)
    try:
        ua_parsed = user_agents.parse(user_agent)
        # CORREÇÃO: Substituído LoginHistory por AuditLog
        audit_entry = AuditLog(
            user_id=user.id,
            session_id=sid,
            ip_address=ip,
            user_agent_raw=user_agent,
            device_type="Mobile" if ua_parsed.is_mobile else "Tablet" if ua_parsed.is_tablet else "Desktop",
            browser=f"{ua_parsed.browser.family} {ua_parsed.browser.version_string}",
            os=f"{ua_parsed.os.family} {ua_parsed.os.version_string}",
            login_timestamp=datetime.utcnow(),
            is_active_session=True,
            auth_method="social"
        )
        db.add(audit_entry)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to record AuditLog: {e}")

    # Security: Audit Log
    log_audit(db, user.id, "LOGIN", ip, {"session_id": sid, "method": "social"})

    token = create_access_token({
        "sub": str(user.id),
        "email": user.email,
        "sid": sid
    })

    # STRICT ONBOARDING ENFORCEMENT
    # If user has no GitHub ID, they MUST go to onboarding, regardless of request
    if not user.github_id and redirect_url != "/onboarding/connect-github":
        logger.warning(f"Strict Onboarding Enforcement: Redirecting User {user.id} to GitHub Connect")
        redirect_url = "/onboarding/connect-github"

    # Force Dashboard Redirect (Onboarding Removed)
    response = RedirectResponse(redirect_url, status_code=303)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=(settings.ENVIRONMENT == "production"),
        samesite="lax",
        max_age=604800
    )
    return response

def get_consistent_redirect_uri(request: Request, endpoint: str) -> str:
    """
    Generates a consistent Redirect URI, forcing HTTPS if in production
    or if the app appears to be behind a proxy (implied by http check).
    """
    redirect_uri = str(request.url_for(endpoint))

    # CRITICAL FIX: Unify HTTPS enforcement logic.
    # If we are in production OR the generated URI is HTTP (proxy), we upgrade to HTTPS.
    # This ensures Login and Callback steps use the exact same logic.
    if settings.ENVIRONMENT == 'production' or "http://" in redirect_uri:
        if "http://" in redirect_uri:
            redirect_uri = redirect_uri.replace("http://", "https://")

    return redirect_uri

@router.get("/onboarding/connect-github", response_class=HTMLResponse)
async def connect_github(request: Request, user: User = Depends(get_current_user_onboarding)):
    if not user:
        return RedirectResponse("/login")

    # STRICT SEQUENTIAL FLOW
    # If already connected, move to Dashboard (Zero Touch)
    if user.github_id:
        return RedirectResponse("/dashboard", status_code=303)

    return templates.TemplateResponse("onboarding_github.html", {"request": request, "user": user})


@router.get("/login/github")
@limiter.limit("5/minute")
async def login_github(request: Request):
    # STRICT AUTH CHECK: GitHub is secondary step ONLY
    if not getattr(request.state, "user", None):
        return RedirectResponse("/login?error=linkedin_required_first")

    if not settings.GITHUB_CLIENT_ID:
        return RedirectResponse("/login?error=github_not_configured")

    # Generate redirect_uri and FORCE HTTPS
    redirect_uri = get_consistent_redirect_uri(request, 'auth_github_callback')

    logger.info(f"🔎 GITHUB LOGIN START: Generated Redirect URI: {redirect_uri}")

    # SECURITY REFACTOR: Use authorize_redirect which manages state automatically
    return await oauth.github.authorize_redirect(request, redirect_uri)

@router.get("/auth/github/callback")
async def auth_github_callback(request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    ip = get_client_ip(request)

    # EXTREME VERBOSITY LOGGING
    code = request.query_params.get('code')
    state = request.query_params.get('state')
    error = request.query_params.get('error')
    code_log = code[:5] if code else "None"
    logger.info(f"📥 GITHUB CALLBACK RECEIVED: Code={code_log}... | State={state} | Error={error}")

    try:
        # STRICT AUTH CHECK
        current_user_state = getattr(request.state, "user", None)
        if not current_user_state:
            # This should not happen if /login/github is protected, but safeguards callback attacks
            logger.warning("GitHub Callback attempted without session")
            return RedirectResponse("/login?error=session_expired_github")

        # 1. Manual HTTPS Enforcement
        redirect_uri = get_consistent_redirect_uri(request, 'auth_github_callback')

        logger.info(f"🔄 GITHUB TOKEN EXCHANGE: URI={redirect_uri}")

        # 2. SECURITY REFACTOR: Use fetch_access_token (Prevents Collision)
        # FIX: Manual fetch to avoid auto-extraction collision
        token = await oauth.github.fetch_access_token(
            redirect_uri=redirect_uri,
            code=str(request.query_params.get('code')),
            grant_type='authorization_code'
        )

        logger.info(f"🔑 GITHUB TOKEN RECEIVED: {token.get('access_token')[:5]}... | Scope: {token.get('scope')}")

        resp = await oauth.github.get('user', token=token)
        profile = resp.json()

        logger.info(f"👤 GITHUB PROFILE: ID={profile.get('id')} | Email={profile.get('email')}")

        # Get email (might be private)
        email = profile.get('email')
        if not email:
            logger.warning("⚠️ Email null in profile. Fetching /user/emails...")
            resp_emails
