import os
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

# 1. Set required env vars BEFORE importing app modules to pass config validation
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
# We import social router specifically to patch the object where it lives
from app.main import app
from app.routes import social

client = TestClient(app)

def test_linkedin_login_nonce_is_none():
    """
    Verifies that the /login/linkedin endpoint calls authorize_redirect with nonce=None.
    """
    # Patch the 'oauth.linkedin' object found in 'app.routes.social'
    with patch("app.routes.social.oauth.linkedin") as mock_linkedin:
        # Configure mock to return a simple response (like a string URL or similar)
        # The route expects await ... so it must be async or return an awaitable if not mocked as AsyncMock
        # However, authorize_redirect is async.
        # authlib's authorize_redirect returns a Starlette Response (RedirectResponse).

        # We need to simulate the awaitable if the code does `await ...`
        # But if we use MagicMock and the code is `await mock()`, MagicMock isn't awaitable by default unless it is an AsyncMock.
        # Let's try to use AsyncMock if available (python 3.8+).
        try:
            from unittest.mock import AsyncMock
            mock_linkedin.authorize_redirect = AsyncMock()
        except ImportError:
            # Fallback for older python if needed, but 3.8+ is standard now.
            # If AsyncMock is not available, we can just return a future or use a coroutine.
            async def async_mock(*args, **kwargs):
                return "Mocked Redirect"
            mock_linkedin.authorize_redirect = MagicMock(side_effect=async_mock)

        # Set return value to a valid response object so the route doesn't crash on return
        from fastapi.responses import RedirectResponse
        mock_linkedin.authorize_redirect.return_value = RedirectResponse("http://testserver/auth/linkedin/callback")

        # Trigger the route
        response = client.get("/login/linkedin", follow_redirects=False)

        # Verify the route didn't crash
        assert response.status_code == 307 or response.status_code == 302

        # Verify authorize_redirect was called
        assert mock_linkedin.authorize_redirect.called

        # Inspect arguments
        call_args = mock_linkedin.authorize_redirect.call_args
        kwargs = call_args.kwargs

        # CRITICAL ASSERTION: nonce must be strictly None
        assert "nonce" in kwargs, "The 'nonce' argument was not passed to authorize_redirect"
        assert kwargs["nonce"] is None, f"Expected nonce=None, but got: {kwargs['nonce']}"

def test_linkedin_callback_claims_options():
    """
    Verifies that /auth/linkedin/callback calls authorize_access_token with
    claims_options={'nonce': {'required': False}} and NO 'value' key.
    """
    with patch("app.routes.social.oauth.linkedin") as mock_linkedin:
        # Mock authorize_access_token
        try:
            from unittest.mock import AsyncMock
            mock_linkedin.authorize_access_token = AsyncMock()
        except ImportError:
             pass

        # We need to mock the token return value to avoid further crashes in the route
        # The route accesses token.get('userinfo') or calls userinfo()
        mock_token = {'userinfo': {'sub': '123', 'email': 'test@example.com', 'name': 'Test User'}}
        mock_linkedin.authorize_access_token.return_value = mock_token

        # Trigger the callback
        # We need to bypass the `get_db` dependency or just let it fail later?
        # The route uses `db: Session = Depends(get_db)`. TestClient handles Depends usually if app is configured.
        # But we don't have a real DB here.
        # We should override the dependency or mock it.
        # However, for this specific test, we just want to check the call to authorize_access_token which happens early.
        # Wait, the code calls `authorize_access_token` inside the try block.

        # To avoid DB issues, let's override get_db to return a mock
        from app.db.session import get_db
        app.dependency_overrides[get_db] = lambda: MagicMock()

        response = client.get("/auth/linkedin/callback")

        # Verify call
        assert mock_linkedin.authorize_access_token.called
        call_args = mock_linkedin.authorize_access_token.call_args
        kwargs = call_args.kwargs

        assert "claims_options" in kwargs
        nonce_options = kwargs["claims_options"].get("nonce", {})

        # CRITICAL CHECK: required=False and NO 'value'
        assert nonce_options.get("required") is False
        assert "value" not in nonce_options, f"Found 'value' in nonce options: {nonce_options.get('value')}"

        # Clean up dependency override
        app.dependency_overrides = {}
