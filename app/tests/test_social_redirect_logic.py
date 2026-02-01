import os
import pytest
from unittest.mock import MagicMock, patch
from fastapi import Request

# Import the module to test
# We rely on pre-set env vars to avoid import errors
from app.routes import social

def test_redirect_uri_dev_http_domain():
    """
    If environment is development AND domain is http,
    we should respect the http scheme (no force https).
    """
    with patch("app.routes.social.settings") as mock_settings:
        mock_settings.ENVIRONMENT = "development"
        mock_settings.DOMAIN = "http://localhost:8000"

        mock_request = MagicMock(spec=Request)
        # url_for returns a string (URL)
        mock_request.url_for.return_value = "http://localhost:8000/auth/callback"

        uri = social.get_consistent_redirect_uri(mock_request, "dummy_endpoint")
        assert uri == "http://localhost:8000/auth/callback"

def test_redirect_uri_dev_https_domain():
    """
    If environment is development BUT domain is configured as https (e.g. staging on Railway),
    we MUST force https.
    """
    with patch("app.routes.social.settings") as mock_settings:
        mock_settings.ENVIRONMENT = "development"
        mock_settings.DOMAIN = "https://staging.app.com"

        mock_request = MagicMock(spec=Request)
        # Internal app sees http due to proxy
        mock_request.url_for.return_value = "http://staging.app.com/auth/callback"

        uri = social.get_consistent_redirect_uri(mock_request, "dummy_endpoint")
        assert uri == "https://staging.app.com/auth/callback"

def test_redirect_uri_prod():
    """
    If environment is production, we MUST force https regardless of domain config
    (though domain should be https in prod).
    """
    with patch("app.routes.social.settings") as mock_settings:
        mock_settings.ENVIRONMENT = "production"
        mock_settings.DOMAIN = "http://misconfigured.com"

        mock_request = MagicMock(spec=Request)
        mock_request.url_for.return_value = "http://misconfigured.com/auth/callback"

        uri = social.get_consistent_redirect_uri(mock_request, "dummy_endpoint")
        assert uri == "https://misconfigured.com/auth/callback"
