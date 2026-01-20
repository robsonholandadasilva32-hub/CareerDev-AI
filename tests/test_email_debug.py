import os
import sys
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, MagicMock

# Add app to path
sys.path.append(os.getcwd())

from app.main import app

@pytest.mark.asyncio
async def test_debug_email_route():
    # Mock send_raw_email to avoid actual sending
    async def mock_send_email_func(*args, **kwargs):
        return True

    with patch("app.routes.debug.send_raw_email", side_effect=mock_send_email_func) as mock_send_async:

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/debug/test-email?to_email=test@example.com")

        assert response.status_code == 200
        assert response.json() == {"status": "success", "message": "Email sent to test@example.com"}
        mock_send_async.assert_called_once()
        args, _ = mock_send_async.call_args
        assert args[0] == "test@example.com"

@pytest.mark.asyncio
async def test_debug_email_route_error():
    async def mock_error(*args, **kwargs):
        raise Exception("SMTP Connection Failed")

    with patch("app.routes.debug.send_raw_email", side_effect=mock_error):
         async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.get("/debug/test-email?to_email=fail@example.com")

         assert response.status_code == 200 # The route returns 200 with error message in JSON
         assert response.json() == {"status": "error", "message": "SMTP Connection Failed"}
