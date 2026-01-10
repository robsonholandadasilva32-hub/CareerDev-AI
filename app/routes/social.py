from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth
from app.core.config import settings

router = APIRouter()

oauth = OAuth()

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

@router.get("/login/github")
async def login_github(request: Request):
    if not settings.GITHUB_CLIENT_ID:
        return "GitHub Login not configured (Missing Client ID)"

    redirect_uri = request.url_for('auth_github_callback')
    return await oauth.github.authorize_redirect(request, redirect_uri)

@router.get("/auth/github/callback")
async def auth_github_callback(request: Request):
    if not settings.GITHUB_CLIENT_ID:
        return RedirectResponse("/login")

    try:
        token = await oauth.github.authorize_access_token(request)
        resp = await oauth.github.get('user', token=token)
        profile = resp.json()

        # Here we would:
        # 1. Check if user exists by email (profile['email'])
        # 2. If yes, log them in (create JWT)
        # 3. If no, create account + log in

        # For now, just showing we got the data
        print(f"GitHub User: {profile.get('login')}")
        return RedirectResponse(url="/dashboard")

    except Exception as e:
        print(f"GitHub Auth Error: {e}")
        return RedirectResponse("/login?error=github_failed")
