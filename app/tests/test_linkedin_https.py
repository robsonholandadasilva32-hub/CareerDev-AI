import os
import pytest
from unittest.mock import AsyncMock, patch

# Set env vars required for app startup
os.environ.setdefault("SMTP_HOST", "smtp.example.com")
os.environ.setdefault("SMTP_PORT", "587")
os.environ.setdefault("SMTP_USER", "user")
os.environ.setdefault("SMTP_PASSWORD", "password")
os.environ.setdefault("LINKEDIN_CLIENT_ID", "mock_id")
os.environ.setdefault("LINKEDIN_CLIENT_SECRET", "mock_secret")
os.environ.setdefault("GITHUB_CLIENT_ID", "mock_gh_id")
os.environ.setdefault("GITHUB_CLIENT_SECRET", "mock_gh_secret")

from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")

@pytest.mark.asyncio
async def test_linkedin_login_forces_https_redirect_uri(client):
    # Ensure linkedin client is registered (might be already by app startup, but safe to check)
    from app.routes.social import oauth

    # Patch authorize_redirect
    with patch('app.routes.social.oauth.linkedin.authorize_redirect', new_callable=AsyncMock) as mock_authorize:
        # Mock return value to avoid errors in route
        from fastapi.responses import RedirectResponse
        mock_authorize.return_value = RedirectResponse("https://www.linkedin.com/oauth/authorize?...")

        # Act: Request with HTTP base url (default for TestClient/AsyncClient)
        response = await client.get("/login/linkedin", follow_redirects=False)

        # Assert
        assert mock_authorize.called

        # Check arguments passed to authorize_redirect
        args, kwargs = mock_authorize.call_args

        # redirect_uri is usually the second positional arg or a kwarg
        # Definition: authorize_redirect(request, redirect_uri=None, ...)

        redirect_uri = None
        if len(args) > 1:
            redirect_uri = args[1]
        elif 'redirect_uri' in kwargs:
            redirect_uri = kwargs['redirect_uri']

        assert redirect_uri is not None
        assert isinstance(redirect_uri, str)
        assert redirect_uri.startswith("https://")
        assert "auth/linkedin/callback" in redirect_uri

@pytest.mark.asyncio
async def test_github_login_forces_https_redirect_uri(client):
    # Patch authorize_redirect for GitHub
    with patch('app.routes.social.oauth.github.authorize_redirect', new_callable=AsyncMock) as mock_authorize:
        from fastapi.responses import RedirectResponse
        mock_authorize.return_value = RedirectResponse("https://github.com/login/oauth/authorize?...")

        response = await client.get("/login/github", follow_redirects=False)

        assert mock_authorize.called

        args, kwargs = mock_authorize.call_args
        redirect_uri = None
        if len(args) > 1:
            redirect_uri = args[1]
        elif 'redirect_uri' in kwargs:
            redirect_uri = kwargs['redirect_uri']

        assert redirect_uri is not None
        assert isinstance(redirect_uri, str)
        assert redirect_uri.startswith("https://")
        assert "auth/github/callback" in redirect_uri
