import pytest
from unittest.mock import MagicMock, patch
from fastapi import Request

# Import the module to test
# We rely on pre-set env vars to avoid import errors
from app.routes import social

def test_redirect_uri_uses_configured_domain():
    """
    The redirect URI must strictly follow settings.DOMAIN, regardless of the request context.
    """
    with patch("app.routes.social.settings") as mock_settings:
        mock_settings.DOMAIN = "https://www.careerdev-ai.online"

        mock_request = MagicMock(spec=Request)
        # Mock app.url_path_for
        mock_request.app.url_path_for.return_value = "/auth/linkedin/callback"

        uri = social.get_consistent_redirect_uri(mock_request, "auth_linkedin_callback")
        assert uri == "https://www.careerdev-ai.online/auth/linkedin/callback"

def test_redirect_uri_handles_trailing_slash():
    """
    Ensure no double slashes if DOMAIN ends with /
    """
    with patch("app.routes.social.settings") as mock_settings:
        mock_settings.DOMAIN = "https://example.com/"

        mock_request = MagicMock(spec=Request)
        mock_request.app.url_path_for.return_value = "/callback"

        uri = social.get_consistent_redirect_uri(mock_request, "dummy")
        assert uri == "https://example.com/callback"

def test_redirect_uri_ignores_request_scheme():
    """
    Even if the request comes in as HTTP (e.g. internal proxy),
    the redirect URI should use the configured DOMAIN scheme (HTTPS).
    """
    with patch("app.routes.social.settings") as mock_settings:
        mock_settings.DOMAIN = "https://secure.com"

        mock_request = MagicMock(spec=Request)
        # Request context is HTTP
        mock_request.url.scheme = "http"
        mock_request.app.url_path_for.return_value = "/login/callback"

        uri = social.get_consistent_redirect_uri(mock_request, "dummy")
        assert uri == "https://secure.com/login/callback"
