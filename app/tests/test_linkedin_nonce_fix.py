import os
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import Request

# Set env vars BEFORE importing app modules to pass validation and enable LinkedIn registration
os.environ["SMTP_HOST"] = "smtp.example.com"
os.environ["LINKEDIN_CLIENT_SECRET"] = "dummy_linkedin_secret"
os.environ["GITHUB_CLIENT_SECRET"] = "dummy_github_secret"
os.environ["LINKEDIN_CLIENT_ID"] = "dummy_linkedin_id"

# Import after setting env vars
from app.routes.social import login_linkedin

@pytest.mark.asyncio
async def test_login_linkedin_passes_static_nonce():
    """
    Verifies that login_linkedin calls authorize_redirect with nonce="global_bypass_nonce".
    This is required to prevent Authlib from generating a random nonce.
    """
    # Mock the request object
    mock_request = MagicMock(spec=Request)
    mock_request.url_for.return_value = "http://localhost/auth/linkedin/callback"

    # We patch the 'oauth' object in app.routes.social
    # specifically the 'linkedin' attribute on it.
    with patch("app.routes.social.oauth.linkedin") as mock_linkedin_client:
        mock_linkedin_client.authorize_redirect = AsyncMock(return_value="mock_response")

        # Call the route handler
        await login_linkedin(mock_request)

        # Assertions
        mock_linkedin_client.authorize_redirect.assert_called_once()

        # Check arguments passed to authorize_redirect
        call_args = mock_linkedin_client.authorize_redirect.call_args
        _, kwargs = call_args

        # Verify nonce="global_bypass_nonce" is explicitly passed
        if "nonce" not in kwargs:
            pytest.fail("nonce argument was NOT passed to authorize_redirect")

        expected = "global_bypass_nonce"
        assert kwargs["nonce"] == expected, f"Expected nonce='{expected}', but got '{kwargs['nonce']}'"
