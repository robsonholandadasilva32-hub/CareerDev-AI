import os
import pytest
from unittest.mock import MagicMock, patch
from fastapi import Request
from app.routes import social

def test_redirect_uri_always_uses_domain_setting():
    """
    The redirect URI should ALWAYS be constructed from settings.DOMAIN,
    ignoring the incoming request host or scheme.
    """
    with patch("app.routes.social.settings") as mock_settings:
        # Case 1: Production HTTPS
        mock_settings.DOMAIN = "https://www.careerdev-ai.online"

        mock_request = MagicMock(spec=Request)
        mock_request.app.url_path_for.return_value = "/auth/callback"

        uri = social.get_consistent_redirect_uri(mock_request, "dummy_endpoint")
        assert uri == "https://www.careerdev-ai.online/auth/callback"

        # Case 2: Development HTTP
        mock_settings.DOMAIN = "http://localhost:8000"
        uri = social.get_consistent_redirect_uri(mock_request, "dummy_endpoint")
        assert uri == "http://localhost:8000/auth/callback"

def test_redirect_uri_strips_trailing_slash():
    """
    Ensure we don't get double slashes if DOMAIN has a trailing slash.
    """
    with patch("app.routes.social.settings") as mock_settings:
        mock_settings.DOMAIN = "https://www.careerdev-ai.online/"

        mock_request = MagicMock(spec=Request)
        mock_request.app.url_path_for.return_value = "/auth/callback"

        uri = social.get_consistent_redirect_uri(mock_request, "dummy_endpoint")
        assert uri == "https://www.careerdev-ai.online/auth/callback"
