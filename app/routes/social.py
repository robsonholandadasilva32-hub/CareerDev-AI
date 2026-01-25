from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from authlib.integrations.starlette_client import OAuth
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.session import get_db
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
        logger.critical(f"✅ DB COMMIT SUCCESS: User {user.id} logged in.")
    except Exception as e:
        logger.critical(f"❌ DB COMMIT FAILED: {e}")
        raise e

    # Security: Create Session
    ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "unknown")
    logger.info(f"Creating session for user {user.id} | IP: {ip} | UA: {user_agent[:30]}...")
    sid = create_user_session(db, user.id, ip, user_agent)

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

    logger.critical(f"🔎 GITHUB LOGIN START: Generated Redirect URI: {redirect_uri}")

    # SECURITY REFACTOR: Use authorize_redirect which manages state automatically
    return await oauth.github.authorize_redirect(request, redirect_uri)

@router.get("/auth/github/callback")
async def auth_github_callback(request: Request, db: Session = Depends(get_db)):
    ip = get_client_ip(request)

    # EXTREME VERBOSITY LOGGING
    code = request.query_params.get('code')
    state = request.query_params.get('state')
    error = request.query_params.get('error')
    code_log = code[:5] if code else "None"
    logger.critical(f"📥 GITHUB CALLBACK RECEIVED: Code={code_log}... | State={state} | Error={error}")

    try:
        # STRICT AUTH CHECK
        current_user_state = getattr(request.state, "user", None)
        if not current_user_state:
            # This should not happen if /login/github is protected, but safeguards callback attacks
            logger.warning("GitHub Callback attempted without session")
            return RedirectResponse("/login?error=session_expired_github")

        # 1. Manual HTTPS Enforcement
        redirect_uri = get_consistent_redirect_uri(request, 'auth_github_callback')

        logger.critical(f"🔄 GITHUB TOKEN EXCHANGE: URI={redirect_uri}")

        # 2. SECURITY REFACTOR: Use authorize_access_token (Enforces State Validation)
        # This replaces manual fetch_access_token
        # FIX: Pass redirect_uri EXPLICITLY to match authorize_redirect
        token = await oauth.github.authorize_access_token(request, redirect_uri=redirect_uri)

        logger.critical(f"🔑 GITHUB TOKEN RECEIVED: {token.get('access_token')[:5]}... | Scope: {token.get('scope')}")

        resp = await oauth.github.get('user', token=token)
        profile = resp.json()

        logger.critical(f"👤 GITHUB PROFILE: ID={profile.get('id')} | Email={profile.get('email')}")

        # Get email (might be private)
        email = profile.get('email')
        if not email:
            logger.critical("⚠️ Email null in profile. Fetching /user/emails...")
            resp_emails = await oauth.github.get('user/emails', token=token)
            emails = resp_emails.json()
            for e in emails:
                if e.get('primary') and e.get('verified'):
                    email = e['email']
                    break
            logger.critical(f"📧 EMAIL FETCHED: {email}")

        if not email:
             log_audit(db, None, "SOCIAL_ERROR", ip, "GitHub: No email found")
             return RedirectResponse("/login?error=github_no_email")

        github_id = str(profile.get('id'))
        name = profile.get('name') or profile.get('login')
        avatar = profile.get('avatar_url')

        # --- STRICT LINKING LOGIC ---
        # Re-fetch user attached to current session
        current_user = db.query(User).filter(User.id == current_user_state.id).first()
        if not current_user:
             return RedirectResponse("/login?error=user_not_found")

        # Check for conflict
        existing_user = get_user_by_github_id(db, github_id)
        if existing_user and existing_user.id != current_user.id:
            log_audit(db, current_user.id, "CONNECT_SOCIAL_FAIL", ip, "GitHub: Account already linked to another user")
            return RedirectResponse("/onboarding/connect-github?error=github_taken", status_code=302)

        # Update User
        current_user.github_id = github_id
        if not current_user.avatar_url:
            current_user.avatar_url = avatar

        # ZERO TOUCH: Automatically complete profile
        current_user.is_profile_completed = True
        current_user.terms_accepted = True
        current_user.terms_accepted_at = datetime.utcnow()

        db.commit() # Sync commit
        logger.critical(f"✅ GITHUB LINKED: User {current_user.id} updated.")

        log_audit(db, current_user.id, "CONNECT_SOCIAL", ip, "GitHub Connected")

        # Check Security Badge
        check_and_award_security_badge(db, current_user)

        # Redirect Directly to Dashboard (Zero Touch)
        return RedirectResponse("/dashboard", status_code=303)

    except Exception as e:
        logger.critical(f"🔥 GITHUB ERROR: {str(e)}", exc_info=True)
        log_audit(db, None, "SOCIAL_ERROR", ip, f"GitHub Exception: {e}")
        return RedirectResponse("/login?error=github_failed")

@router.get("/login/linkedin")
@limiter.limit("5/minute")
async def login_linkedin(request: Request):
    if not settings.LINKEDIN_CLIENT_ID:
        return RedirectResponse("/login?error=linkedin_not_configured")

    # Generate redirect_uri and FORCE HTTPS
    redirect_uri = get_consistent_redirect_uri(request, 'auth_linkedin_callback')

    logger.critical(f"🔎 LINKEDIN LOGIN START: Generated Redirect URI: {redirect_uri}")

    # SECURITY REFACTOR: Remove nonce=None to allow default state handling if applicable, or ensure state is managed.
    # Authlib default is to generate state.
    return await oauth.linkedin.authorize_redirect(request, redirect_uri)

@router.get("/auth/linkedin/callback")
async def auth_linkedin_callback(request: Request, db: Session = Depends(get_db)):
    ip = get_client_ip(request)

    # EXTREME VERBOSITY LOGGING
    code = request.query_params.get('code')
    state = request.query_params.get('state')
    error = request.query_params.get('error')
    code_log = code[:5] if code else "None"
    logger.critical(f"📥 LINKEDIN CALLBACK RECEIVED: Code={code_log}... | State={state} | Error={error}")

    try:
        # 1. Manual HTTPS Enforcement (Crucial for Railway)
        redirect_uri = get_consistent_redirect_uri(request, 'auth_linkedin_callback')

        logger.critical(f"🔄 LINKEDIN TOKEN EXCHANGE: URI={redirect_uri}")

        # 2. SECURITY REFACTOR: Use authorize_access_token (Enforces State Validation)
        # This replaces manual fetch_access_token
        # FIX: LinkedIn OIDC sometimes omits 'nonce', causing 500 errors.
        # Validation relaxed via claims_options per Deep Diagnostic Resolution.
        # FIX: Pass redirect_uri EXPLICITLY
        token = await oauth.linkedin.authorize_access_token(
            request,
            redirect_uri=redirect_uri,
            claims_options={"nonce": {"required": False}}
        )

        logger.critical(f"🔑 LINKEDIN TOKEN RECEIVED: {token.get('access_token')[:5]}...")

        user_info = await oauth.linkedin.userinfo(token=token)

        logger.critical(f"👤 LINKEDIN USER INFO: {json.dumps(user_info, default=str)}")

        if not user_info:
             logger.error("LinkedIn Error: No user info received")
             log_audit(db, None, "SOCIAL_ERROR", ip, "LinkedIn: No user info received")
             return RedirectResponse("/login?error=linkedin_failed")

        # Support OIDC 'sub' and legacy 'id'
        linkedin_id = user_info.get('sub') or user_info.get('id')
        if not linkedin_id:
             logger.error(f"LinkedIn Error: No ID found in user_info. Keys: {list(user_info.keys())}")
             log_audit(db, None, "SOCIAL_ERROR", ip, "LinkedIn: No ID found")
             return RedirectResponse("/login?error=linkedin_failed")

        email = user_info.get('email')
        
        # Robust name extraction
        name = user_info.get('name')
        if not name:
             first = user_info.get('given_name')
             last = user_info.get('family_name')
             if first and last:
                 name = f"{first} {last}"
             else:
                 name = "LinkedIn User" # Fallback

        picture = user_info.get('picture')

        if not email:
             logger.warning(f"LinkedIn Error: No email found in user_info. Keys: {list(user_info.keys())}")
             log_audit(db, None, "SOCIAL_ERROR", ip, "LinkedIn: No email found")
             return RedirectResponse("/login?error=missing_linkedin_email")

        # 1. Check by Email (Fix: Prioritize Email to prevent loop)
        user = get_user_by_email(db, email)
        if user:
            logger.info(f"DEBUG: Found existing user: {user.id}")
            # Update ID if missing
            if user.linkedin_id != linkedin_id:
                user.linkedin_id = linkedin_id
                if not user.avatar_url:
                    user.avatar_url = picture
                db.commit() # Fix: Sync commit
                logger.critical(f"✅ USER UPDATED: {user.id} LinkedIn ID Linked.")

                # Check Security Badge
                check_and_award_security_badge(db, user)

            return login_user_and_redirect(request, user, db, redirect_url="/dashboard")

        # 2. Check by ID (Legacy/Fallback)
        user = get_user_by_linkedin_id(db, linkedin_id)
        if user:
            return login_user_and_redirect(request, user, db, redirect_url="/dashboard")

        # 3. Create User (with Idempotency Check)
        logger.info("DEBUG: Creating new user")
        pwd = secrets.token_urlsafe(16)
        hashed_password = await asyncio.to_thread(hash_password, pwd)
        try:
            user = await create_user_async(
                db=db,
                name=name,
                email=email,
                hashed_password=hashed_password,
                linkedin_id=linkedin_id,
                avatar_url=picture,
                email_verified=True
            )
            # ZERO TOUCH: Implicit acceptance
            user.terms_accepted = True
            user.terms_accepted_at = datetime.utcnow()
            db.commit()
            logger.critical(f"✅ NEW USER CREATED: {user.id} ({email})")

        except IntegrityError:
            # Race condition: User created in parallel
            db.rollback()
            logger.warning(f"LinkedIn Race Condition: User {email} already exists. Fetching...")
            user = get_user_by_email(db, email)
            if not user:
                 user = get_user_by_linkedin_id(db, linkedin_id)
            if not user:
                 raise Exception("IntegrityError caught but user not found on retry.")

            # Update missing ID if needed
            if not user.linkedin_id:
                user.linkedin_id = linkedin_id
                db.commit()
                # Check Security Badge
                check_and_award_security_badge(db, user)

        logger.info(f"Strict Onboarding: New user created.")
        return login_user_and_redirect(request, user, db, redirect_url="/dashboard")

    except Exception as e:
        logger.critical(f"🔥 LINKEDIN ERROR: {str(e)}", exc_info=True)
        log_audit(db, None, "SOCIAL_ERROR", ip, f"LinkedIn Exception: {e}")
        return RedirectResponse("/login?error=linkedin_failed")
