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
from app.core.config import settings

@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")

@pytest.mark.asyncio
async def test_linkedin_login_respects_http_in_dev(client):
    # Ensure environment is not production
    original_env = settings.ENVIRONMENT
    settings.ENVIRONMENT = 'development'

    try:
        # Patch authorize_redirect
        with patch('app.routes.social.oauth.linkedin.authorize_redirect', new_callable=AsyncMock) as mock_authorize:
            from fastapi.responses import RedirectResponse
            mock_authorize.return_value = RedirectResponse("https://www.linkedin.com/oauth/authorize?...")

            # Act: Request with HTTP base url
            response = await client.get("/login/linkedin", follow_redirects=False)

            # Assert
            assert mock_authorize.called
            args, kwargs = mock_authorize.call_args
            redirect_uri = kwargs.get('redirect_uri') or args[1]

            assert redirect_uri is not None
            # Expect http because environment is dev and client is http://test
            assert redirect_uri.startswith("http://")
            assert "auth/linkedin/callback" in redirect_uri
    finally:
        settings.ENVIRONMENT = original_env

@pytest.mark.asyncio
async def test_linkedin_login_forces_https_in_prod(client):
    # Force production environment
    original_env = settings.ENVIRONMENT
    settings.ENVIRONMENT = 'production'

    try:
        with patch('app.routes.social.oauth.linkedin.authorize_redirect', new_callable=AsyncMock) as mock_authorize:
            from fastapi.responses import RedirectResponse
            mock_authorize.return_value = RedirectResponse("https://www.linkedin.com/oauth/authorize?...")

            # Act: Request with HTTP base url
            response = await client.get("/login/linkedin", follow_redirects=False)

            # Assert
            assert mock_authorize.called
            args, kwargs = mock_authorize.call_args
            redirect_uri = kwargs.get('redirect_uri') or args[1]

            assert redirect_uri is not None
            # Expect https because environment is production
            assert redirect_uri.startswith("https://")
            assert "auth/linkedin/callback" in redirect_uri
    finally:
        settings.ENVIRONMENT = original_env
