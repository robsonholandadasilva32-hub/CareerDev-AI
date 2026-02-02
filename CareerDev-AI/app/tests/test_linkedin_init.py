import os
import pytest
from unittest.mock import AsyncMock, patch

# Set env vars required for app startup BEFORE imports
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
async def test_linkedin_login_redirect_uri_type(client):
    """
    Verifies that the redirect_uri passed to authorize_redirect is a primitive str,
    not a Starlette URL object. This prevents serialization issues in Authlib.
    """

    # Ensure linkedin client is registered (mock environment usually lacks credentials)
    from app.routes.social import oauth
    if 'linkedin' not in oauth._registry:
         oauth.register(
            name='linkedin',
            client_id='mock_id',
            client_secret='mock_secret',
            server_metadata_url='https://www.linkedin.com/oauth/.well-known/openid-configuration',
            client_kwargs={'scope': 'openid profile email'}
        )

    # Mock settings to ensure LINKEDIN_CLIENT_ID is present so the route doesn't return early error
    with patch.object(settings, 'LINKEDIN_CLIENT_ID', 'mock_id'):

        # Patch the authorize_redirect method on the oauth.linkedin object
        with patch('app.routes.social.oauth.linkedin.authorize_redirect', new_callable=AsyncMock) as mock_auth:
            # We don't care about the return value for this test, as we are inspecting the call arguments.
            # But the route awaits it, so it must be awaitable (AsyncMock handles this).
            mock_auth.return_value = None

            # Act
            # We don't follow redirects because authorize_redirect usually returns a RedirectResponse
            await client.get("/login/linkedin", follow_redirects=False)

            # Assert
            assert mock_auth.call_count == 1, "authorize_redirect should be called exactly once"

            call_args = mock_auth.call_args
            args = call_args[0]
            kwargs = call_args[1]

            # authorize_redirect(request, redirect_uri, ...)
            # args[0] is request
            # args[1] should be redirect_uri

            redirect_uri = None
            if len(args) > 1:
                redirect_uri = args[1]
            elif 'redirect_uri' in kwargs:
                redirect_uri = kwargs['redirect_uri']

            assert redirect_uri is not None, "redirect_uri was not found in arguments"

            # The Fix Verification:
            # We explicitly check that it is a 'str' and NOT a 'URL' object (or anything else)
            assert isinstance(redirect_uri, str), f"Expected redirect_uri to be <class 'str'>, but got {type(redirect_uri)}"

            # Check nonce
            assert kwargs.get('nonce') is None, "nonce should be explicitly set to None"
