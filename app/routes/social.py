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
    create_user
)
from app.core.security import hash_password
from app.core.jwt import create_access_token
import secrets
import logging
import os
import asyncio

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

def login_user_and_redirect(request: Request, user):
    token = create_access_token({
        "sub": str(user.id),
        "email": user.email,
        "2fa": False # Social login skips 2FA usually
    })
    response = RedirectResponse("/dashboard", status_code=302)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=request.url.scheme == "https", # Auto-detect HTTPS
        samesite="lax"
    )
    return response

@router.get("/login/github")
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
    try:
        token = await oauth.github.authorize_access_token(request)
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
                    email = e['email']
                    break

        if not email:
             return RedirectResponse("/login?error=github_no_email")

        github_id = str(profile.get('id'))
        name = profile.get('name') or profile.get('login')
        avatar = profile.get('avatar_url')

        # 1. Check by ID
        user = get_user_by_github_id(db, github_id)
        if user:
            return login_user_and_redirect(request, user)

        # 2. Check by Email
        user = get_user_by_email(db, email)
        if user:
            user.github_id = github_id
            if not user.avatar_url:
                user.avatar_url = avatar
            db.commit()
            return login_user_and_redirect(request, user)

        # 3. Create User
        pwd = secrets.token_urlsafe(16)
        hashed_password = await asyncio.to_thread(hash_password, pwd)
        user = create_user(
            db=db,
            name=name,
            email=email,
            hashed_password=hashed_password,
            github_id=github_id,
            avatar_url=avatar,
            email_verified=True # Trusted provider
        )
        return login_user_and_redirect(request, user)

    except Exception as e:
        logger.error(f"GitHub Error: {e}")
        return RedirectResponse("/login?error=github_failed")

@router.get("/login/linkedin")
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
    try:
        logger.info("LinkedIn Auth: Switching to manual fetch_access_token to bypass OIDC validation")

        # 1. Manually extract the code from the URL
        code = request.query_params.get('code')
        if not code:
            logger.error("LinkedIn Error: No code found in callback URL")
            return RedirectResponse("/login?error=linkedin_failed")

        # 2. Pass the code explicitly.
        # DO NOT pass redirect_uri (it's pulled from session).
        # KEEP grant_type.
        token = await oauth.linkedin.fetch_access_token(
            request,
            grant_type='authorization_code',
            code=code
        )

        # 3. Manually fetch user info using the valid token
        user_info = await oauth.linkedin.userinfo(token=token)
        
        # DEBUG: Log user_info
        logger.debug(f"LinkedIn User Data: {user_info}")

        if not user_info:
             logger.error("LinkedIn Error: No user info received")
             return RedirectResponse("/login?error=linkedin_failed")

        # Support OIDC 'sub' and legacy 'id'
        linkedin_id = user_info.get('sub') or user_info.get('id')
        if not linkedin_id:
             logger.error(f"LinkedIn Error: No ID found in user_info. Keys: {list(user_info.keys())}")
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
             return RedirectResponse("/login?error=missing_linkedin_email")

        # 1. Check by ID
        user = get_user_by_linkedin_id(db, linkedin_id)
        if user:
            return login_user_and_redirect(request, user)

        # 2. Check by Email
        user = get_user_by_email(db, email)
        if user:
            user.linkedin_id = linkedin_id
            if not user.avatar_url:
                user.avatar_url = picture
            db.commit()
            return login_user_and_redirect(request, user)

        # 3. Create User
        pwd = secrets.token_urlsafe(16)
        hashed_password = await asyncio.to_thread(hash_password, pwd)
        user = create_user(
            db=db,
            name=name,
            email=email,
            hashed_password=hashed_password,
            linkedin_id=linkedin_id,
            avatar_url=picture,
            email_verified=True
        )
        return login_user_and_redirect(request, user)

    except Exception as e:
        logger.exception(f"LinkedIn Error: {e}")
        return RedirectResponse("/login?error=linkedin_failed")