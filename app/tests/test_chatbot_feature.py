import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import MagicMock, patch, AsyncMock
from app.main import app

@pytest.fixture
def mock_auth():
    with patch("app.routes.chatbot.get_current_user_from_request") as mock:
        yield mock

@pytest.mark.asyncio
async def test_trigger_challenge_endpoint(mock_auth):
    # Mock User ID
    mock_auth.return_value = 1

    # Mock Service to avoid real DB/OpenAI
    with patch("app.routes.chatbot.chatbot_service") as mock_service:
        # Configure the method as async
        mock_service.get_response = AsyncMock(return_value={
            "message": "Challenge Q",
            "meta": {"mode": "challenge"}
        })

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/chatbot/message",
                json={"message": "/trigger_challenge", "mode": "standard", "lang": "en"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["response"] == "Challenge Q"
            assert data["meta"]["mode"] == "challenge"
