from fastapi import APIRouter, Request, Depends, BackgroundTasks
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from authlib.integrations.starlette_client import OAuth
from sqlalchemy.orm import Session, joinedload
from app.core.config import settings
from app.db.session import get_db, SessionLocal
from app.services.social_harvester import social_harvester
from app.db.crud.users import (
    get_user_by_email,
    get_user_by_github_id,
    get_user_by_linkedin_id,
    create_user
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

    # Security: Forensics & Audit
    device_type = "Unknown"
    browser_info = "Unknown"
    os_info = "Unknown"

    try:
        ua_parsed = user_agents.parse(user_agent)
        device_type = "Mobile" if ua_parsed.is_mobile else "Tablet" if ua_parsed.is_tablet else "Desktop"
        browser_info = f"{ua_parsed.browser.family} {ua_parsed.browser.version_string}"
        os_info = f"{ua_parsed.os.family} {ua_parsed.os.version_string}"
    except Exception as e:
        logger.error(f"Failed to parse User Agent: {e}")

    log_audit(
        db=db,
        user_id=user.id,
        action="LOGIN",
        ip_address=ip,
        details={
            "method": "social",
            "session_id": sid,
            "device_info": {
                "user_agent": user_agent,
                "device": device_type,
                "os": os_info,
                "browser": browser_info
            }
        },
        device_type=device_type,
        browser=browser_info,
        os=os_info,
        user_agent_raw=user_agent
    )

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
        secure=(request.url.scheme == "https"),
        samesite="lax",
        max_age=604800
    )
    return response

def get_consistent_redirect_uri(request: Request, endpoint: str) -> str:
    """
    Generates a consistent Redirect URI.
    Forces HTTPS if configured domain is HTTPS or environment is production.
    """
    redirect_uri = str(request.url_for(endpoint))

    # CRITICAL FIX: Unify HTTPS enforcement logic.
    # Force HTTPS if we are in production OR if the main domain is HTTPS (Railway, etc.)
    # This prevents Protocol Mismatch errors when behind a proxy.
    force_https = (settings.ENVIRONMENT == 'production') or (settings.DOMAIN.startswith("https://"))

    if force_https and "http://" in redirect_uri:
        redirect_uri = redirect_uri.replace("http://", "https://")

    return redirect_uri

@router.get("/onboarding/connect-github", response_class=HTMLResponse)
async def connect_github(request: Request, user: User = Depends(get_current_user_onboarding)):
    if not user:
        return RedirectResponse("/login")

    # STRICT SEQUENTIAL FLOW
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

    return await oauth.github.authorize_redirect(request, redirect_uri)

@router.get("/auth/github/callback")
async def auth_github_callback(request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    ip = get_client_ip(request)

    code = request.query_params.get('code')
    state = request.query_params.get('state')
    error = request.query_params.get('error')
    code_log = code[:5] if code else "None"
    logger.info(f"📥 GITHUB CALLBACK RECEIVED: Code={code_log}... | State={state} | Error={error}")

    try:
        current_user_state = getattr(request.state, "user", None)
        if not current_user_state:
            logger.warning("GitHub Callback attempted without session")
            return RedirectResponse("/login?error=session_expired_github")

        # 1. Manual HTTPS Enforcement
        redirect_uri = get_consistent_redirect_uri(request, 'auth_github_callback')

        logger.info(f"🔄 GITHUB TOKEN EXCHANGE: URI={redirect_uri}")

        # 2. SECURITY REFACTOR: Use fetch_access_token
        token = await oauth.github.fetch_access_token(
            redirect_uri=redirect_uri,
            code=str(request.query_params.get('code')),
            grant_type='authorization_code'
        )

        logger.info(f"🔑 GITHUB TOKEN RECEIVED: {token.get('access_token')[:5]}... | Scope: {token.get('scope')}")

        resp = await oauth.github.get('user', token=token)
        profile = resp.json()

        logger.info(f"👤 GITHUB PROFILE: ID={profile.get('id')} | Email={profile.get('email')}")

        email = profile.get('email')
        if not email:
            logger.warning("⚠️ Email null in profile. Fetching /user/emails...")
            resp_emails = await oauth.github.get('user/emails', token=token)
            emails = resp_emails.json()
            for e in emails:
                if e.get('primary') and e.get('verified'):
                    email = e['email']
                    break
            logger.info(f"📧 EMAIL FETCHED: {email}")

        if not email:
             await asyncio.to_thread(
                 log_audit,
                 db=db,
                 user_id=None,
                 action="SOCIAL_ERROR",
                 ip_address=ip,
                 details="GitHub: No email found"
             )
             return RedirectResponse("/login?error=github_no_email")

        github_id = str(profile.get('id'))
        name = profile.get('name') or profile.get('login')
        avatar = profile.get('avatar_url')

        # --- STRICT LINKING LOGIC ---
        # PERFORMANCE OPTIMIZATION: Offload sync DB ops to thread
        result = await asyncio.to_thread(
            _process_github_connect_sync,
            db,
            current_user_state.id,
            github_id,
            token.get('access_token'),
            avatar,
            ip
        )

        if result == "user_not_found":
             return RedirectResponse("/login?error=user_not_found")

        if result == "github_taken":
            return RedirectResponse("/onboarding/connect-github?error=github_taken", status_code=302)

        if token.get('access_token'):
            background_tasks.add_task(social_harvester.harvest_github_data, current_user_state.id, token.get('access_token'))

        return RedirectResponse("/dashboard", status_code=303)

    except Exception as e:
        logger.error(f"🔥 GITHUB ERROR: {str(e)}", exc_info=True)
        await asyncio.to_thread(
            log_audit,
            db=db,
            user_id=None,
            action="SOCIAL_ERROR",
            ip_address=ip,
            details=f"GitHub Exception: {e}"
        )
        return RedirectResponse("/login?error=github_failed")

@router.get("/login/linkedin")
@limiter.limit("5/minute")
async def login_linkedin(request: Request):
    if not settings.LINKEDIN_CLIENT_ID:
        return RedirectResponse("/login?error=linkedin_not_configured")

    if settings.LINKEDIN_REDIRECT_URI:
        redirect_uri = settings.LINKEDIN_REDIRECT_URI
    else:
        redirect_uri = get_consistent_redirect_uri(request, 'auth_linkedin_callback')

    logger.info(f"🔎 LINKEDIN LOGIN START: Generated Redirect URI: {redirect_uri}")

    return await oauth.linkedin.authorize_redirect(request, redirect_uri)

def _process_github_connect_sync(db: Session, user_id: int, github_id: str, token_str: str, avatar: str, ip: str) -> str:
    """
    Synchronous helper to handle GitHub connection logic.
    Offloaded to a thread to prevent blocking the event loop.
    """
    current_user = db.query(User).filter(User.id == user_id).first()
    if not current_user:
         return "user_not_found"

    # Check for conflict
    existing_user = get_user_by_github_id(db, github_id)
    if existing_user and existing_user.id != current_user.id:
        log_audit(
            db=db,
            user_id=current_user.id,
            action="CONNECT_SOCIAL_FAIL",
            ip_address=ip,
            details="GitHub: Account already linked to another user"
        )
        return "github_taken"

    # Update User
    current_user.github_id = github_id
    current_user.github_token = token_str
    if not current_user.avatar_url:
        current_user.avatar_url = avatar

    # ZERO TOUCH: Automatically complete profile
    current_user.is_profile_completed = True
    current_user.terms_accepted = True
    current_user.terms_accepted_at = datetime.utcnow()

    db.commit()
    logger.info(f"✅ GITHUB LINKED: User {current_user.id} updated.")

    log_audit(
        db=db,
        user_id=current_user.id,
        action="CONNECT_SOCIAL",
        ip_address=ip,
        details="GitHub Connected"
    )

    check_and_award_security_badge(db, current_user)

    return "success"

def _process_linkedin_login_sync(user_info: dict, token_data: dict, ip: str, user_agent: str, production_env: bool) -> dict:
    """
    Handles the entire LinkedIn login/signup transactional flow in a separate thread.
    Uses its own Session to ensure thread safety and non-blocking I/O on main loop.
    """
    token_str = token_data.get('access_token')

    linkedin_id = user_info.get('sub') or user_info.get('id')
    email = user_info.get('email')
    picture = user_info.get('picture')

    name = user_info.get('name')
    if not name:
        first = user_info.get('given_name')
        last = user_info.get('family_name')
        if first and last:
            name = f"{first} {last}"
        else:
            name = "LinkedIn User"

    if not linkedin_id:
        return {"status": "error", "error": "linkedin_no_id", "message": "No ID found in user_info"}

    if not email:
        return {"status": "error", "error": "linkedin_no_email", "message": "No email found in user_info"}

    with SessionLocal() as db:
        try:
            # 1. Find User (Email or ID)
            user = db.query(User).options(joinedload(User.career_profile)).filter(User.email == email).first()

            if not user:
                user = db.query(User).options(joinedload(User.career_profile)).filter(User.linkedin_id == linkedin_id).first()

            if user:
                # UPDATE Existing
                logger.info(f"DEBUG: Found existing user: {user.id}")
                if user.linkedin_id != linkedin_id:
                    user.linkedin_id = linkedin_id
                    if not user.avatar_url:
                        user.avatar_url = picture

                user.linkedin_token = token_str
                db.commit()
                logger.info(f"✅ USER UPDATED: {user.id} LinkedIn ID Linked.")

                if user.linkedin_id == linkedin_id:
                    check_and_award_security_badge(db, user)

            else:
                # CREATE New
                logger.info("DEBUG: Creating new user")
                pwd = secrets.token_urlsafe(32)
                hashed_password = hash_password(pwd) # CPU bound, fine here

                try:
                    user = create_user(
                        db=db,
                        name=name,
                        email=email,
                        hashed_password=hashed_password,
                        linkedin_id=linkedin_id,
                        avatar_url=picture,
                        email_verified=True
                    )

                    # ZERO TOUCH
                    user.terms_accepted = True
                    user.terms_accepted_at = datetime.utcnow()
                    user.linkedin_token = token_str
                    db.commit()

                    # Refresh with profile
                    user = db.query(User).options(joinedload(User.career_profile)).filter(User.id == user.id).first()
                    logger.info(f"✅ NEW USER CREATED: {user.id} ({email})")

                except IntegrityError:
                    db.rollback()
                    logger.warning(f"LinkedIn Race Condition: User {email} already exists. Fetching...")
                    user = db.query(User).options(joinedload(User.career_profile)).filter(User.email == email).first()
                    if not user:
                        user = db.query(User).options(joinedload(User.career_profile)).filter(User.linkedin_id == linkedin_id).first()

                    if not user:
                        return {"status": "error", "error": "integrity_error", "message": "IntegrityError but user not found"}

                    if not user.linkedin_id:
                        user.linkedin_id = linkedin_id

                    user.linkedin_token = token_str
                    db.commit()
                    check_and_award_security_badge(db, user)

            # 2. LOGIN LOGIC (From login_user_and_redirect)
            user.last_login = datetime.utcnow()
            if not user.terms_accepted:
                user.terms_accepted = True
                user.terms_accepted_at = datetime.utcnow()

            if user.linkedin_id and user.github_id and user.terms_accepted:
                user.is_profile_completed = True

            db.commit() # Save login stats

            # Session & Audit
            sid = create_user_session(db, user.id, ip, user_agent)

            # Security: Forensics & Audit
            device_type = "Unknown"
            browser_info = "Unknown"
            os_info = "Unknown"

            try:
                ua_parsed = user_agents.parse(user_agent)
                device_type = "Mobile" if ua_parsed.is_mobile else "Tablet" if ua_parsed.is_tablet else "Desktop"
                browser_info = f"{ua_parsed.browser.family} {ua_parsed.browser.version_string}"
                os_info = f"{ua_parsed.os.family} {ua_parsed.os.version_string}"
            except Exception as e:
                logger.error(f"Failed to parse User Agent: {e}")

            log_audit(
                db=db,
                user_id=user.id,
                action="LOGIN",
                ip_address=ip,
                details={
                    "method": "social",
                    "provider": "linkedin",
                    "session_id": sid,
                    "device_info": {
                        "user_agent": user_agent,
                        "device": device_type,
                        "os": os_info,
                        "browser": browser_info
                    }
                },
                device_type=device_type,
                browser=browser_info,
                os=os_info,
                user_agent_raw=user_agent
            )

            # Generate Token
            token = create_access_token({
                "sub": str(user.id),
                "email": user.email,
                "sid": sid
            })

            # Determine Redirect
            redirect_url = "/dashboard"
            if not user.github_id:
                redirect_url = "/onboarding/connect-github"

            return {
                "status": "success",
                "user_id": user.id,
                "token": token,
                "redirect_url": redirect_url
            }

        except Exception as e:
            logger.error(f"🔥 Sync Processing Error: {e}", exc_info=True)
            return {"status": "error", "error": "internal_error", "message": str(e)}

@router.get("/auth/linkedin/callback")
async def auth_linkedin_callback(request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # Note: 'db' dependency is not used for the heavy lifting anymore, only for lightweight or legacy parts if needed.
    # The sync helper creates its own session.

    ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "unknown")

    code = request.query_params.get('code')
    state = request.query_params.get('state')
    error = request.query_params.get('error')
    code_log = code[:5] if code else "None"
    logger.info(f"📥 LINKEDIN CALLBACK RECEIVED: Code={code_log}... | State={state} | Error={error}")

    try:
        # 1. Manual HTTPS Enforcement
        if settings.LINKEDIN_REDIRECT_URI:
            redirect_uri = settings.LINKEDIN_REDIRECT_URI
        else:
            redirect_uri = get_consistent_redirect_uri(request, 'auth_linkedin_callback')

        logger.info(f"🔄 LINKEDIN TOKEN EXCHANGE: URI={redirect_uri}")

        # 2. Exchange Token
        token_data = await oauth.linkedin.fetch_access_token(
            redirect_uri=redirect_uri,
            code=str(request.query_params.get('code')),
            grant_type='authorization_code'
        )
        token_str = token_data.get('access_token')
        logger.info(f"🔑 LINKEDIN TOKEN RECEIVED: {token_str[:5]}...")

        user_info = await oauth.linkedin.userinfo(token=token_data)
        logger.info(f"👤 LINKEDIN USER INFO: {json.dumps(user_info, default=str)}")

        if not user_info:
             logger.error("LinkedIn Error: No user info received")
             # We can use the passed 'db' for this quick audit log
             await asyncio.to_thread(
                 log_audit,
                 db=db,
                 user_id=None,
                 action="SOCIAL_ERROR",
                 ip_address=ip,
                 details="LinkedIn: No user info received"
             )
             return RedirectResponse("/login?error=linkedin_failed")

        # 3. Offload Blocking DB Operations to Thread
        result = await asyncio.to_thread(
            _process_linkedin_login_sync,
            user_info,
            token_data,
            ip,
            user_agent,
            (settings.ENVIRONMENT == "production")
        )

        if result["status"] == "error":
            err_code = result.get("error", "unknown")
            msg = result.get("message", "")
            log_audit(
                db=db,
                user_id=None,
                action="SOCIAL_ERROR",
                ip_address=ip,
                details=f"LinkedIn Process Error: {msg}"
            )

            if err_code == "linkedin_no_id" or err_code == "linkedin_no_email":
                 return RedirectResponse("/login?error=linkedin_failed")

            return RedirectResponse(f"/login?error={err_code}")

        # 4. Trigger Background Data Harvest
        if token_str:
            background_tasks.add_task(social_harvester.harvest_linkedin_data, result["user_id"], token_str)

        # 5. Create Response
        response = RedirectResponse(result["redirect_url"], status_code=303)
        response.set_cookie(
            key="access_token",
            value=result["token"],
            httponly=True,
            secure=(request.url.scheme == "https"),
            samesite="lax",
            max_age=604800
        )
        return response

    except Exception as e:
        logger.error(f"🔥 LINKEDIN ERROR: {str(e)}", exc_info=True)
        # Safe fallback audit
        try:
             await asyncio.to_thread(
                 log_audit,
                 db=db,
                 user_id=None,
                 action="SOCIAL_ERROR",
                 ip_address=ip,
                 details=f"LinkedIn Exception: {e}"
             )
        except:
             pass
        return RedirectResponse("/login?error=linkedin_failed")
