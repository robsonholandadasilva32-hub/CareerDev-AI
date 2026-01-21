import os
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

# Set env vars required for social routes to register oauth clients BEFORE imports
os.environ["GITHUB_CLIENT_ID"] = "dummy_github_id"
os.environ["GITHUB_CLIENT_SECRET"] = "dummy_github_secret"
os.environ["LINKEDIN_CLIENT_ID"] = "dummy_linkedin_id"
os.environ["LINKEDIN_CLIENT_SECRET"] = "dummy_linkedin_secret"
os.environ["SMTP_HOST"] = "smtp.example.com"
os.environ["SMTP_PORT"] = "587"
os.environ["SMTP_USER"] = "user"
os.environ["SMTP_PASSWORD"] = "password"

# Now import app
from fastapi.testclient import TestClient
from fastapi.responses import RedirectResponse
from app.main import app

def test_github_redirect_uri_is_string():
    with patch("app.routes.social.oauth.github.authorize_redirect", new_callable=AsyncMock) as mock_authorize:
        # Mock must return a Response object to prevent FastAPI from trying to JSON-encode the Mock
        mock_authorize.return_value = RedirectResponse("http://github.com/login")

        client = TestClient(app)
        response = client.get("/login/github", follow_redirects=False)

        assert mock_authorize.called
        # Check arguments
        args, kwargs = mock_authorize.call_args
        request = args[0]
        redirect_uri = args[1]

        assert isinstance(redirect_uri, str), f"Expected redirect_uri to be str, got {type(redirect_uri)}"
        assert "auth/github/callback" in redirect_uri

def test_linkedin_redirect_uri_is_string():
    with patch("app.routes.social.oauth.linkedin.authorize_redirect", new_callable=AsyncMock) as mock_authorize:
        # Mock must return a Response object
        mock_authorize.return_value = RedirectResponse("http://linkedin.com/login")

        client = TestClient(app)
        response = client.get("/login/linkedin", follow_redirects=False)

        assert mock_authorize.called
        # Check arguments
        args, kwargs = mock_authorize.call_args
        request = args[0]
        redirect_uri = args[1]

        assert isinstance(redirect_uri, str), f"Expected redirect_uri to be str, got {type(redirect_uri)}"
        assert "auth/linkedin/callback" in redirect_uri
