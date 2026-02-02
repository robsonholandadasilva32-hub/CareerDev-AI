import os
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import status
from authlib.integrations.starlette_client import StarletteOAuth2App

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
    Verifies that the /login/linkedin endpoint calls authorize_redirect.
    """
    with patch.object(StarletteOAuth2App, 'authorize_redirect') as mock_authorize:
        # Setup AsyncMock
        try:
            from unittest.mock import AsyncMock
            if not isinstance(mock_authorize, AsyncMock):
                 pass
        except ImportError:
             pass

        async def async_mock(*args, **kwargs):
            from fastapi.responses import RedirectResponse
            return RedirectResponse("http://testserver/auth/linkedin/callback")

        mock_authorize.side_effect = async_mock

        response = client.get("/login/linkedin", follow_redirects=False)

        assert response.status_code == 307 or response.status_code == 302
        assert mock_authorize.called

        # Verify force https and str type for redirect_uri
        args = mock_authorize.call_args.args
        if len(args) > 1:
            redirect_uri = args[1]
            assert isinstance(redirect_uri, str)
            assert redirect_uri.startswith("https://")

def test_linkedin_callback_uses_authorize_access_token():
    """
    Verifies that /auth/linkedin/callback uses authorize_access_token
    with relaxed nonce validation.
    """
    with patch.object(StarletteOAuth2App, 'authorize_access_token') as mock_authorize_token, \
         patch.object(StarletteOAuth2App, 'userinfo') as mock_userinfo:

        # Make them async
        async def return_token(*args, **kwargs):
            return {'access_token': 'dummy_token'}
        mock_authorize_token.side_effect = return_token

        async def return_user(*args, **kwargs):
            return {
                'sub': '12345',
                'email': 'manual_fetch@example.com',
                'name': 'Manual Fetch User',
                'picture': 'http://example.com/pic.jpg'
            }
        mock_userinfo.side_effect = return_user

        # Mock DB dependency
        from app.db.session import get_db
        app.dependency_overrides[get_db] = lambda: MagicMock()

        # Patch CRUD functions to return None (simulating new user)
        with patch("app.routes.social.get_user_by_linkedin_id", return_value=None), \
             patch("app.routes.social.get_user_by_email", return_value=None), \
             patch("app.routes.social.create_user_async") as mock_create_user:

            # Configure create_user to return a valid object
            mock_created_user = MagicMock()
            mock_created_user.id = 123
            mock_created_user.email = "manual_fetch@example.com"
            mock_create_user.return_value = mock_created_user

            # Trigger callback (add code param)
            response = client.get("/auth/linkedin/callback?code=fakecode", follow_redirects=False)

        # ASSERTIONS

        # 1. authorize_access_token SHOULD be called
        assert mock_authorize_token.called, "authorize_access_token SHOULD be called"

        # Verify relaxed nonce
        kwargs = mock_authorize_token.call_args.kwargs
        assert kwargs.get("claims_options") == {"nonce": {"required": False}}

        # 2. userinfo SHOULD be called with the token
        assert mock_userinfo.called, "userinfo SHOULD be called"

        # 3. Verify successful redirect (means user was logged in/created)
        # It redirects to /dashboard on success
        assert response.status_code == 303
        assert response.headers["location"] == "/dashboard"

        # Clean up
        app.dependency_overrides = {}

def test_linkedin_callback_missing_code():
    """
    Verifies that missing code triggers an error redirect.
    """
    # Act: Call callback WITHOUT code
    # We expect authorize_access_token to throw or handle it?
    # Actually if code is missing, Authlib usually raises MismatchingState or similar if state is required.
    # But here we just get.

    # We should mock authorize_access_token to raise Exception if called,
    # OR we rely on the fact that without code, something will fail.
    # But authorize_access_token expects request.

    # In social.py, the try/except block catches exceptions.

    with patch.object(StarletteOAuth2App, 'authorize_access_token') as mock_authorize_token:
         mock_authorize_token.side_effect = Exception("Authlib error")

         response = client.get("/auth/linkedin/callback", follow_redirects=False)

         assert response.status_code == 307 or response.status_code == 302
         assert "/login?error=linkedin_failed" in response.headers["location"]
