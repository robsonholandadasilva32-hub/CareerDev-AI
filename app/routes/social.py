from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
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
from datetime import datetime
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)

router = APIRouter()
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

def login_user_and_redirect(request: Request, user, db: Session, redirect_url: str = "/dashboard"):
    # Update last_login
    user.last_login = datetime.utcnow()
    db.commit()

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

@router.get("/login/github")
@limiter.limit("5/minute")
async def login_github(request: Request):
    if not settings.GITHUB_CLIENT_ID:
        return RedirectResponse("/login?error=github_not_configured")

    # Generate redirect_uri and FORCE HTTPS
    redirect_uri = str(request.url_for('auth_github_callback'))
    if "http://" in redirect_uri:
        redirect_uri = redirect_uri.replace("http://", "https://")

    return await oauth.github.authorize_redirect(request, redirect_uri)

@router.get("/auth/github/callback")
async def auth_github_callback(request: Request, db: Session = Depends(get_db)):
    ip = get_client_ip(request)
    try:
        # 1. Manual HTTPS Enforcement (Crucial for Railway)
        redirect_uri = str(request.url_for('auth_github_callback'))
        if settings.ENVIRONMENT == 'production':
            redirect_uri = redirect_uri.replace('http:', 'https:')

        logger.info(f"GitHub Auth: Using fetch_access_token with redirect_uri={redirect_uri}")

        # 2. Use fetch_access_token (Bypassing authorize_access_token wrapper)
        token = await oauth.github.fetch_access_token(
            redirect_uri=redirect_uri,
            code=str(request.query_params.get('code')),
            grant_type='authorization_code'
        )
        resp = await oauth.github.get('user', token=token)
        profile = resp.json()

        # Get email (might be private)
        email = profile.get('email')
        if not email:
            resp_emails = await oauth.github.get('user/emails', token=token)
            emails = resp_emails.json()
            for e in emails:
                if e.get('primary') and e.get('verified'):
                    email = e['email']
                    break

        if not email:
             log_audit(db, None, "SOCIAL_ERROR", ip, "GitHub: No email found")
             return RedirectResponse("/login?error=github_no_email")

        github_id = str(profile.get('id'))
        name = profile.get('name') or profile.get('login')
        avatar = profile.get('avatar_url')

        # --- LINKING LOGIC (The Loop Fix) ---
        current_user_state = getattr(request.state, "user", None)
        if current_user_state:
            # Re-fetch user attached to current session
            current_user = db.query(User).filter(User.id == current_user_state.id).first()
            if current_user:
                # Check for conflict
                existing_user = get_user_by_github_id(db, github_id)
                if existing_user and existing_user.id != current_user.id:
                    log_audit(db, current_user.id, "CONNECT_SOCIAL_FAIL", ip, "GitHub: Account already linked to another user")
                    return RedirectResponse("/onboarding/connect-github?error=github_taken", status_code=302)

                # Update User
                current_user.github_id = github_id
                if not current_user.avatar_url:
                    current_user.avatar_url = avatar
                db.commit() # Sync commit

                log_audit(db, current_user.id, "CONNECT_SOCIAL", ip, "GitHub Connected")

                # Check Security Badge
                check_and_award_security_badge(db, current_user)

                return RedirectResponse("/dashboard", status_code=303)

        # --- EXISTING LOGIN/REGISTER LOGIC ---

        # 1. Check by Email (Fix: Prioritize Email to prevent loop)
        user = get_user_by_email(db, email)
        if user:
            logger.info(f"DEBUG: Found existing user: {user.id}")
            # Update ID if missing
            if user.github_id != github_id:
                user.github_id = github_id
                if not user.avatar_url:
                    user.avatar_url = avatar
                db.commit() # Fix: Sync commit

                # Check Security Badge
                check_and_award_security_badge(db, user)

            return login_user_and_redirect(request, user, db)

        # 2. Check by ID (Legacy/Fallback)
        user = get_user_by_github_id(db, github_id)
        if user:
            return login_user_and_redirect(request, user, db)

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
                github_id=github_id,
                avatar_url=avatar,
                email_verified=True # Trusted provider
            )
        except IntegrityError:
            # Race condition: User created in parallel
            db.rollback()
            logger.warning(f"GitHub Race Condition: User {email} already exists. Fetching...")
            user = get_user_by_email(db, email)
            if not user:
                 user = get_user_by_github_id(db, github_id)
            if not user:
                 raise Exception("IntegrityError caught but user not found on retry.")

            # Update missing ID if needed
            if not user.github_id:
                user.github_id = github_id
                db.commit()
                # Check Security Badge
                check_and_award_security_badge(db, user)

        return login_user_and_redirect(request, user, db)

    except Exception as e:
        logger.error(f"GitHub Error: {e}")
        log_audit(db, None, "SOCIAL_ERROR", ip, f"GitHub Exception: {e}")
        return RedirectResponse("/login?error=github_failed")

@router.get("/login/linkedin")
@limiter.limit("5/minute")
async def login_linkedin(request: Request):
    if not settings.LINKEDIN_CLIENT_ID:
        return RedirectResponse("/login?error=linkedin_not_configured")

    # Generate redirect_uri and FORCE HTTPS
    redirect_uri = str(request.url_for('auth_linkedin_callback'))
    if "http://" in redirect_uri:
        redirect_uri = redirect_uri.replace("http://", "https://")

    logger.info(f"LinkedIn Login: Starting flow with nonce=None and sanitized redirect_uri={redirect_uri}")

    # Pass the sanitized string
    return await oauth.linkedin.authorize_redirect(request, redirect_uri, nonce=None)

@router.get("/auth/linkedin/callback")
async def auth_linkedin_callback(request: Request, db: Session = Depends(get_db)):
    ip = get_client_ip(request)
    try:
        # 1. Manual HTTPS Enforcement (Crucial for Railway)
        redirect_uri = str(request.url_for('auth_linkedin_callback'))
        if settings.ENVIRONMENT == 'production':
            redirect_uri = redirect_uri.replace('http:', 'https:')

        logger.info(f"LinkedIn Auth: Using fetch_access_token with redirect_uri={redirect_uri}")

        # 2. Use fetch_access_token (Bypassing authorize_access_token wrapper)
        token = await oauth.linkedin.fetch_access_token(
            redirect_uri=redirect_uri,
            code=str(request.query_params.get('code')),
            grant_type='authorization_code'
        )

        user_info = await oauth.linkedin.userinfo(token=token)

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

                # Check Security Badge
                check_and_award_security_badge(db, user)

            # STRICT ONBOARDING: Check GitHub
            target = "/dashboard"
            if not user.github_id:
                logger.info("Strict Onboarding: User missing GitHub. Redirecting to GitHub auth.")
                target = "/login/github"

            return login_user_and_redirect(request, user, db, redirect_url=target)

        # 2. Check by ID (Legacy/Fallback)
        user = get_user_by_linkedin_id(db, linkedin_id)
        if user:
            # STRICT ONBOARDING: Check GitHub
            target = "/dashboard"
            if not user.github_id:
                logger.info("Strict Onboarding: User missing GitHub. Redirecting to GitHub auth.")
                target = "/login/github"
            return login_user_and_redirect(request, user, db, redirect_url=target)

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

        # STRICT ONBOARDING: New user definitely needs GitHub
        target = "/login/github"
        if user.github_id: # Should not happen for new user via LinkedIn unless found via email
            target = "/dashboard"

        logger.info(f"Strict Onboarding: New user created. Redirecting to {target}")
        return login_user_and_redirect(request, user, db, redirect_url=target)

    except Exception as e:
        logger.exception(f"LinkedIn Error: {e}")
        log_audit(db, None, "SOCIAL_ERROR", ip, f"LinkedIn Exception: {e}")
        return RedirectResponse("/login?error=linkedin_failed")
