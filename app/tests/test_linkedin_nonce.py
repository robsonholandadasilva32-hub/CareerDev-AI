import os
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import status

# 1. Set required env vars BEFORE importing app modules
os.environ["SMTP_HOST"] = "smtp.example.com"
os.environ["SMTP_PORT"] = "587"
os.environ["SMTP_USER"] = "user"
os.environ["SMTP_PASSWORD"] = "pass"
os.environ["LINKEDIN_CLIENT_ID"] = "dummy_linkedin_id"
os.environ["LINKEDIN_CLIENT_SECRET"] = "dummy_linkedin_secret"
os.environ["GITHUB_CLIENT_ID"] = "dummy_gh_id"
os.environ["GITHUB_CLIENT_SECRET"] = "dummy_gh_secret"
os.environ["SECRET_KEY"] = "dummy_secret_key"
os.environ["SESSION_SECRET_KEY"] = "dummy_session_key"

# 2. Import app and routes
from app.main import app
from app.routes import social

client = TestClient(app)

def test_linkedin_login_nonce_is_none():
    """
    Verifies that the /login/linkedin endpoint calls authorize_redirect with nonce=None.
    """
    with patch("app.routes.social.oauth.linkedin") as mock_linkedin:
        # Setup AsyncMock
        try:
            from unittest.mock import AsyncMock
            mock_linkedin.authorize_redirect = AsyncMock()
        except ImportError:
            async def async_mock(*args, **kwargs):
                return "Mocked Redirect"
            mock_linkedin.authorize_redirect = MagicMock(side_effect=async_mock)

        from fastapi.responses import RedirectResponse
        mock_linkedin.authorize_redirect.return_value = RedirectResponse("http://testserver/auth/linkedin/callback")

        response = client.get("/login/linkedin", follow_redirects=False)

        assert response.status_code == 307 or response.status_code == 302
        assert mock_linkedin.authorize_redirect.called
        kwargs = mock_linkedin.authorize_redirect.call_args.kwargs
        assert "nonce" in kwargs
        assert kwargs["nonce"] is None

        # Verify force https and str type for redirect_uri
        args = mock_linkedin.authorize_redirect.call_args.args
        if len(args) > 1:
            redirect_uri = args[1]
            assert isinstance(redirect_uri, str)
            assert redirect_uri.startswith("https://")

def test_linkedin_callback_manual_fetch():
    """
    Verifies that /auth/linkedin/callback uses fetch_access_token + userinfo
    instead of authorize_access_token (which enforces OIDC validation).
    """
    with patch("app.routes.social.oauth.linkedin") as mock_linkedin:
        # Setup AsyncMocks
        try:
            from unittest.mock import AsyncMock
            mock_linkedin.fetch_access_token = AsyncMock()
            mock_linkedin.userinfo = AsyncMock()
            mock_linkedin.authorize_access_token = AsyncMock()
        except ImportError:
             pass

        # Mock returns
        mock_token = {'access_token': 'dummy_token'}
        mock_linkedin.fetch_access_token.return_value = mock_token

        mock_user = {
            'sub': '12345',
            'email': 'manual_fetch@example.com',
            'name': 'Manual Fetch User',
            'picture': 'http://example.com/pic.jpg'
        }
        mock_linkedin.userinfo.return_value = mock_user

        # Mock DB dependency
        from app.db.session import get_db
        app.dependency_overrides[get_db] = lambda: MagicMock()

        # Patch CRUD functions to return None (simulating new user)
        # We need to patch where they are IMPORTED in social.py
        with patch("app.routes.social.get_user_by_linkedin_id", return_value=None), \
             patch("app.routes.social.get_user_by_email", return_value=None), \
             patch("app.routes.social.create_user") as mock_create_user:

            # Configure create_user to return a valid object with ID and email
            mock_created_user = MagicMock()
            mock_created_user.id = 123
            mock_created_user.email = "manual_fetch@example.com"
            # Ensure attributes used in JWT are simple types, not Mocks
            # MagicMock attributes are Mocks by default. We must set them to primitives.
            # However, logic is user.email. user.id.
            # If I set them as above, they are primitives.
            mock_create_user.return_value = mock_created_user

            # Trigger callback (add code param)
            response = client.get("/auth/linkedin/callback?code=fakecode", follow_redirects=False)

        # ASSERTIONS

        # 1. authorize_access_token should NOT be called
        assert not mock_linkedin.authorize_access_token.called, "authorize_access_token should NOT be called"

        # 2. fetch_access_token SHOULD be called with explicit grant_type and redirect_uri
        assert mock_linkedin.fetch_access_token.called, "fetch_access_token SHOULD be called"
        fetch_kwargs = mock_linkedin.fetch_access_token.call_args.kwargs
        assert fetch_kwargs.get("grant_type") == "authorization_code"

        # Redirect_uri should NOT be passed manually
        assert "redirect_uri" not in fetch_kwargs

        # 3. userinfo SHOULD be called with the token
        assert mock_linkedin.userinfo.called, "userinfo SHOULD be called"

        # Verify arguments for userinfo call
        userinfo_kwargs = mock_linkedin.userinfo.call_args.kwargs
        assert userinfo_kwargs.get('token') == mock_token

        # 4. Verify successful redirect (means user was logged in/created)
        # It redirects to /dashboard on success
        assert response.status_code == 302
        assert response.headers["location"] == "/dashboard"

        # Clean up
        app.dependency_overrides = {}
